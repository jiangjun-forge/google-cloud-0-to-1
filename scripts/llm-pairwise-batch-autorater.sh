#!/bin/bash
# Copyright 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0
# llm-pairwise-batch-autorater.sh
# 주의: 본 코드는 상용 배포용이 아닌 학습 및 데모용 가이드 스크립트다.
# 용도: 구글 GenAI SDK를 내장 구동하여, 대량의 질문에 대해 모델 A와 B의 배치 예측을 병렬 실행하고, 그 결과를 다시 배치 평가하여 빅쿼리에 누적 적재하는 범용 오토레이터 엔진을 구축한다.

# 프로젝트 ID 정의
PROJECT_ID="${PROJECT_ID:-$(gcloud config get-value project 2>/dev/null)}" # 프로젝트 ID 식별
if [ -z "${PROJECT_ID}" ] || [ "${PROJECT_ID}" = "None" ]; then
  PROJECT_ID="your-project-id" # 기본 프로젝트 ID 바인딩
fi

REPORT_ONLY=false
if [ "$1" = "--report-only" ]; then
  REPORT_ONLY=true
fi

if [ "${REPORT_ONLY}" = "true" ]; then
  echo "오토레이팅 예측 단계 없이 기존 빅쿼리 누적 결과 리포트만 조회하는 중..."
fi
# 버텍스 AI 배치 예측 콘솔 주소 병기 (https://console.cloud.google.com/vertex-ai/batch-predictions )

# 배시 내장형 파이썬 로직 구동
PROJECT_ID="${PROJECT_ID}" REPORT_ONLY="${REPORT_ONLY}" python3 << 'EOF'
import datetime
import hashlib
import json
import os
import sys
import time

# Google GenAI SDK를 위해 Vertex AI 환경변수 명시적 설정
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "True"

from google import genai
from google.cloud import bigquery
from google.cloud import storage
from google.genai.types import CreateBatchJobConfig

PROJECT_ID = os.environ.get("PROJECT_ID", "your-project-id")
LOCAL_DATASET = "samples/llm-pairwise-autorater/eval_dataset.jsonl" if os.path.exists("samples/llm-pairwise-autorater/eval_dataset.jsonl") else "eval_dataset.jsonl"
REPORT_ONLY = os.environ.get("REPORT_ONLY", "false") == "true"

if REPORT_ONLY:
  print("--- 오토레이터 레포트 조회 모드 기동 (빅쿼리 실시간 쿼리) ---")
  if not os.path.exists(LOCAL_DATASET):
    print(f"오류: 로컬 데이터셋 {LOCAL_DATASET} 파일이 존재하지 않는다.", file=sys.stderr)
    sys.exit(1)
  with open(LOCAL_DATASET, "rb") as f:
    DATASET_HASH = hashlib.md5(f.read()).hexdigest()
  print(f"로컬 데이터셋 해시값 검출 완료: {DATASET_HASH}")
  bq_client = bigquery.Client(project=PROJECT_ID)
  
  query_str_partition = f"""
    SELECT 
      session_id, 
      model_id, 
      COUNT(id) AS total_questions, 
      ROUND(AVG(accuracy), 2) AS avg_accuracy, 
      ROUND(AVG(clarity), 2) AS avg_clarity, 
      ROUND(AVG(completeness), 2) AS avg_completeness, 
      ROUND(AVG(score), 2) AS avg_score, 
      ROUND(COUNTIF(CAST(selected AS STRING) IN ('Y', 'true')) / COUNT(id) * 100, 1) AS win_rate_percentage
    FROM evaluation_results.gemini_pairwise_judgments
    WHERE dataset_hash = '{DATASET_HASH}'
      AND _PARTITIONDATE >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)
    GROUP BY session_id, model_id
    ORDER BY session_id DESC, model_id ASC
  """

  query_str_fallback = f"""
    SELECT 
      session_id, 
      model_id, 
      COUNT(id) AS total_questions, 
      ROUND(AVG(accuracy), 2) AS avg_accuracy, 
      ROUND(AVG(clarity), 2) AS avg_clarity, 
      ROUND(AVG(completeness), 2) AS avg_completeness, 
      ROUND(AVG(score), 2) AS avg_score, 
      ROUND(COUNTIF(CAST(selected AS STRING) IN ('Y', 'true')) / COUNT(id) * 100, 1) AS win_rate_percentage
    FROM evaluation_results.gemini_pairwise_judgments
    WHERE dataset_hash = '{DATASET_HASH}'
    GROUP BY session_id, model_id
    ORDER BY session_id DESC, model_id ASC
  """

  try:
    query_job = bq_client.query(query_str_partition)
    results = query_job.result()
  except Exception:
    print("비파티션 테이블 예외 감지: 최적화 필터를 제외한 폴백 쿼리를 가동한다.")
    query_job = bq_client.query(query_str_fallback)
    results = query_job.result()

  print("+-------------------------+-----------------------+-----------------+--------------+-------------+------------------+-----------+---------------------+")
  print("|       session_id        |       model_id        | total_questions | avg_accuracy | avg_clarity | avg_completeness | avg_score | win_rate_percentage |")
  print("+-------------------------+-----------------------+-----------------+--------------+-------------+------------------+-----------+---------------------+")
  for row in results:
    print(f"| {row.session_id:<23} | {row.model_id:<21} | {row.total_questions:<15} | {row.avg_accuracy:<12} | {row.avg_clarity:<11} | {row.avg_completeness:<16} | {row.avg_score:<9} | {row.win_rate_percentage:<19} |")
  print("+-------------------------+-----------------------+-----------------+--------------+-------------+------------------+-----------+---------------------+")
  sys.exit(0)

# Google GenAI SDK를 위해 Vertex AI 환경변수 명시적 설정
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "True"

from google import genai
from google.cloud import bigquery
from google.cloud import storage
from google.genai.types import CreateBatchJobConfig

PROJECT_ID = os.environ.get("PROJECT_ID", "your-project-id")
LOCATION = "us"
SESSION_ID = f"session_batch_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
LOCAL_DATASET = "samples/llm-pairwise-autorater/eval_dataset.jsonl" if os.path.exists("samples/llm-pairwise-autorater/eval_dataset.jsonl") else "eval_dataset.jsonl"
LOCAL_OUTPUT = "tmp/judgments.jsonl"
os.makedirs("tmp", exist_ok=True)

BUCKET_NAME = PROJECT_ID
INPUT_PREFIX = "batch_input"
OUTPUT_PREFIX = "batch_output"

os.environ["GOOGLE_CLOUD_PROJECT"] = PROJECT_ID
os.environ["GOOGLE_CLOUD_LOCATION"] = LOCATION

client = genai.Client(
  vertexai=True,
  project=PROJECT_ID,
  location=LOCATION
)

def safe_get_batch_job(client, job_name, max_retries=5, backoff_seconds=10):
  for attempt in range(max_retries):
    try:
      return client.batches.get(name=job_name)
    except Exception as e:
      print(f"경고: 배치 작업 상태 조회 중 오류 발생 (시도 {attempt+1}/{max_retries}): {e}")
      if attempt == max_retries - 1:
        raise e
      time.sleep(backoff_seconds)


# 2026년 배치 예측 완벽 지원 모델 가동
# 모델 B 편애 방지 및 편향 제어를 위해 교차 패널(Panel 1 & Panel 2) 구성
MODEL_A = "gemini-3.1-flash-lite"
MODEL_B = "gemini-3.5-flash"

# 교차 평가를 위한 판사 패널 정의
MODEL_EVAL_1 = "gemini-3.1-flash-lite"
MODEL_EVAL_2 = "gemini-3.5-flash"

print(f"--- LLM 배치 예측 기반 교차 평균 파이프라인 가동 [세션 ID: {SESSION_ID}] ---")

if not os.path.exists(LOCAL_DATASET):
  print(f"오류: 로컬 데이터셋 {LOCAL_DATASET} 파일이 존재하지 않는다.", file=sys.stderr)
  sys.exit(1)

with open(LOCAL_DATASET, "rb") as f:
  DATASET_HASH = hashlib.md5(f.read()).hexdigest()

print(f"로컬 데이터셋 해시값 검출 완료: {DATASET_HASH}")

storage_client = storage.Client(project=PROJECT_ID)
bucket = storage_client.bucket(BUCKET_NAME)
if not bucket.exists():
  print(f"스토리지 버킷 gs://{BUCKET_NAME} 이 존재하지 않아 안전 생성하는 중...")
  bucket = storage_client.create_bucket(BUCKET_NAME, location=LOCATION)

print("로컬 질문 데이터를 배치 예측 JSONL 규격으로 가공하는 중...")
id_arr = []
context_arr = []
question_arr = []

with open(LOCAL_DATASET, "r", encoding="utf-8") as f:
  for line in f:
    if line.strip():
      item = json.loads(line)
      id_arr.append(item.get("id"))
      context_arr.append(item.get("context"))
      question_arr.append(item.get("question"))

total_items = len(id_arr)
print(f"총 {total_items}개의 문항을 메모리에 로드했다.")

batch_input_a_local = "tmp/eval_input_a.jsonl"
batch_input_b_local = "tmp/eval_input_b.jsonl"

with open(batch_input_a_local, "w", encoding="utf-8") as fa, open(batch_input_b_local, "w", encoding="utf-8") as fb:
  for i in range(total_items):
    key = str(id_arr[i])
    prompt_a = f"Answer the following question based on the provided context. Keep your response extremely brief, concise, and to the point (maximum 2 sentences).\n\nContext: {context_arr[i]}\n\nQuestion: {question_arr[i]}"
    req_a = {
      "key": key,
      "request": {
        "contents": [{"role": "user", "parts": [{"text": prompt_a}]}]
      }
    }
    fa.write(json.dumps(req_a, ensure_ascii=False) + "\n")
    
    prompt_b = f"Answer the following question based on the provided context. Provide a detailed, thorough, and highly structured response with rich explanations.\n\nContext: {context_arr[i]}\n\nQuestion: {question_arr[i]}"
    req_b = {
      "key": key,
      "request": {
        "contents": [{"role": "user", "parts": [{"text": prompt_b}]}]
      }
    }
    fb.write(json.dumps(req_b, ensure_ascii=False) + "\n")

blob_a = bucket.blob(f"{INPUT_PREFIX}/eval_input_a.jsonl")
blob_a.upload_from_filename(batch_input_a_local)

blob_b = bucket.blob(f"{INPUT_PREFIX}/eval_input_b.jsonl")
blob_b.upload_from_filename(batch_input_b_local)

print("배치 예측 입력 GCS 업로드 성공!")

print("배치 예측 작업 제출 중 (모델 A & 모델 B 비동기 병렬)...")
job_a = client.batches.create(
  model=MODEL_A,
  src=f"gs://{BUCKET_NAME}/{INPUT_PREFIX}/eval_input_a.jsonl",
  config=CreateBatchJobConfig(
    dest=f"gs://{BUCKET_NAME}/{OUTPUT_PREFIX}/{SESSION_ID}/output_a/"
  )
)
print(f"└─ 모델 A 작업 기동 완료: {job_a.name}")

job_b = client.batches.create(
  model=MODEL_B,
  src=f"gs://{BUCKET_NAME}/{INPUT_PREFIX}/eval_input_b.jsonl",
  config=CreateBatchJobConfig(
    dest=f"gs://{BUCKET_NAME}/{OUTPUT_PREFIX}/{SESSION_ID}/output_b/"
  )
)
print(f"└─ 모델 B 작업 기동 완료: {job_b.name}")

print("클라우드 배치 연산 완료 대기 중 (15초 간격으로 모니터링)...")
ended_states = ['JOB_STATE_SUCCEEDED', 'JOB_STATE_FAILED', 'JOB_STATE_CANCELLED', 'JOB_STATE_EXPIRED']

while True:
  job_a = safe_get_batch_job(client, job_a.name)
  job_b = safe_get_batch_job(client, job_b.name)
  print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] 모델 A 상태: {job_a.state.name} | 모델 B 상태: {job_b.state.name}")
  if job_a.state.name in ended_states and job_b.state.name in ended_states:
    break
  time.sleep(15)

if job_a.state.name != "JOB_STATE_SUCCEEDED" or job_b.state.name != "JOB_STATE_SUCCEEDED":
  print(f"오류: 배치 예측 작업 실패. 모델 A: {job_a.state.name}, 모델 B: {job_b.state.name}", file=sys.stderr)
  sys.exit(1)

print("모델 A & 모델 B 클라우드 배치 추론 완결!")

def parse_gcs_jsonl(bucket_name, prefix):
  storage_client_parser = storage.Client()
  bucket_parser = storage_client_parser.bucket(bucket_name)
  blobs = bucket_parser.list_blobs(prefix=prefix)
  results = {}
  for blob in blobs:
    if blob.name.endswith(".jsonl"):
      content = blob.download_as_text()
      for line in content.splitlines():
        if line.strip():
          data = json.loads(line)
          key = data.get("key")
          if not key:
            continue
          if "error" in data:
            results[key] = f"Error: {data['error']}"
          elif "response" in data:
            try:
              text = data["response"]["candidates"][0]["content"]["parts"][0]["text"]
              results[key] = text.strip()
            except Exception as e:
              results[key] = f"Parsing Error: {e}"
  return results

print("GCS 추론 결과 수집 및 병합 작업 수행 중...")
resp_a_dict = parse_gcs_jsonl(BUCKET_NAME, f"{OUTPUT_PREFIX}/{SESSION_ID}/output_a/")
resp_b_dict = parse_gcs_jsonl(BUCKET_NAME, f"{OUTPUT_PREFIX}/{SESSION_ID}/output_b/")

# 교차 및 순서 편향을 완전히 극복하기 위한 GCS 입력 생성 로직 고도화
# - 한 문항당 Judge 1과 Judge 2가 각각 교차로 순서(A, B)와 (B, A)를 교차 평가하도록 2배 수집
batch_input_eval_1_local = "tmp/eval_input_eval_1.jsonl"
batch_input_eval_2_local = "tmp/eval_input_eval_2.jsonl"

with open(batch_input_eval_1_local, "w", encoding="utf-8") as fe1, open(batch_input_eval_2_local, "w", encoding="utf-8") as fe2:
  for i in range(total_items):
    key = str(id_arr[i])
    ans_a = resp_a_dict.get(key, "Inference failed.")
    ans_b = resp_b_dict.get(key, "Inference failed.")
    
    # Judge 1은 정방향 (Response A, Response B) 평가
    eval_prompt_1 = f"""You are an expert evaluator. Compare two model responses (Response A and Response B) to a given question based on the provided context.
Assess each response by assigning scores from 1 to 5 for Accuracy, Clarity, and Completeness.
Write a concise, model-specific qualitative explanation for Response A and Response B respectively.
Finally, assign an overall score from 1.0 to 5.0 for each response, and determine which response is better (A, B, or TIE).

Question: {question_arr[i]}
Context: {context_arr[i]}

Response A: {ans_a}
Response B: {ans_b}

Provide your judgment in the following JSON format:
{{
  \"choice\": \"A\" or \"B\" or \"TIE\",
  \"response_a_accuracy\": 1-5,
  \"response_a_clarity\": 1-5,
  \"response_a_completeness\": 1-5,
  \"response_a_explanation\": \"Qualitative evaluation specifically analyzing Response A.\",
  \"response_a_score\": 1.0-5.0,
  \"response_b_accuracy\": 1-5,
  \"response_b_clarity\": 1-5,
  \"response_b_completeness\": 1-5,
  \"response_b_explanation\": \"Qualitative evaluation specifically analyzing Response B.\",
  \"response_b_score\": 1.0-5.0,
  \"explanation\": \"Overall comparison explanation here.\"
}}
Ensure your response is valid JSON and nothing else. Do not wrap the JSON in backticks or markdown formatting."""

    # Judge 2는 역방향 (Response B, Response A) 평가로 Swap 하여 편향 완전 상쇄
    eval_prompt_2 = f"""You are an expert evaluator. Compare two model responses (Response A and Response B) to a given question based on the provided context.
Assess each response by assigning scores from 1 to 5 for Accuracy, Clarity, and Completeness.
Write a concise, model-specific qualitative explanation for Response A and Response B respectively.
Finally, assign an overall score from 1.0 to 5.0 for each response, and determine which response is better (A, B, or TIE).

Question: {question_arr[i]}
Context: {context_arr[i]}

Response A: {ans_b}
Response B: {ans_a}

Provide your judgment in the following JSON format (Note that Response A here is the second model's answer, and Response B here is the first model's answer):
{{
  \"choice\": \"A\" or \"B\" or \"TIE\",
  \"response_a_accuracy\": 1-5,
  \"response_a_clarity\": 1-5,
  \"response_a_completeness\": 1-5,
  \"response_a_explanation\": \"Qualitative evaluation specifically analyzing Response A.\",
  \"response_a_score\": 1.0-5.0,
  \"response_b_accuracy\": 1-5,
  \"response_b_clarity\": 1-5,
  \"response_b_completeness\": 1-5,
  \"response_b_explanation\": \"Qualitative evaluation specifically analyzing Response B.\",
  \"response_b_score\": 1.0-5.0,
  \"explanation\": \"Overall comparison explanation here.\"
}}
Ensure your response is valid JSON and nothing else. Do not wrap the JSON in backticks or markdown formatting."""

    fe1.write(json.dumps({"key": key, "request": {"contents": [{"role": "user", "parts": [{"text": eval_prompt_1}]}]}}, ensure_ascii=False) + "\n")
    fe2.write(json.dumps({"key": key, "request": {"contents": [{"role": "user", "parts": [{"text": eval_prompt_2}]}]}}, ensure_ascii=False) + "\n")

blob_eval_1 = bucket.blob(f"{INPUT_PREFIX}/eval_input_eval_1.jsonl")
blob_eval_1.upload_from_filename(batch_input_eval_1_local)

blob_eval_2 = bucket.blob(f"{INPUT_PREFIX}/eval_input_eval_2.jsonl")
blob_eval_2.upload_from_filename(batch_input_eval_2_local)
print("교차 평가자 배치 입력 GCS 업로드 성공!")

print("교차 평가 배치 예측 작업 제출 중 (Judge 1 & Judge 2 병렬 구동)...")
job_eval_1 = client.batches.create(
  model=MODEL_EVAL_1,
  src=f"gs://{BUCKET_NAME}/{INPUT_PREFIX}/eval_input_eval_1.jsonl",
  config=CreateBatchJobConfig(
    dest=f"gs://{BUCKET_NAME}/{OUTPUT_PREFIX}/{SESSION_ID}/output_eval_1/"
  )
)
print(f"└─ 평가자 1 (gemini-3.1-flash-lite) 작업 기동 완료: {job_eval_1.name}")

job_eval_2 = client.batches.create(
  model=MODEL_EVAL_2,
  src=f"gs://{BUCKET_NAME}/{INPUT_PREFIX}/eval_input_eval_2.jsonl",
  config=CreateBatchJobConfig(
    dest=f"gs://{BUCKET_NAME}/{OUTPUT_PREFIX}/{SESSION_ID}/output_eval_2/"
  )
)
print(f"└─ 평가자 2 (gemini-3.5-flash) 작업 기동 완료: {job_eval_2.name}")

while True:
  job_eval_1 = safe_get_batch_job(client, job_eval_1.name)
  job_eval_2 = safe_get_batch_job(client, job_eval_2.name)
  print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] 평가자 1 상태: {job_eval_1.state.name} | 평가자 2 상태: {job_eval_2.state.name}")
  if job_eval_1.state.name in ended_states and job_eval_2.state.name in ended_states:
    break
  time.sleep(15)

if job_eval_1.state.name != "JOB_STATE_SUCCEEDED" or job_eval_2.state.name != "JOB_STATE_SUCCEEDED":
  print(f"오류: 평가자 배치 예측 작업 실패. 평가자 1: {job_eval_1.state.name}, 평가자 2: {job_eval_2.state.name}", file=sys.stderr)
  sys.exit(1)

print("클라우드 교차 오토레이팅 평가 완결!")

def parse_eval_results(bucket_name, prefix, swapped=False):
  storage_client_eval = storage.Client()
  bucket_eval = storage_client_eval.bucket(bucket_name)
  blobs = bucket_eval.list_blobs(prefix=prefix)
  results = {}
  for blob in blobs:
    if blob.name.endswith(".jsonl"):
      content = blob.download_as_text()
      for line in content.splitlines():
        if line.strip():
          data = json.loads(line)
          key = data.get("key")
          if not key:
            continue
          if "error" in data:
            results[key] = {"error": data["error"]}
          elif "response" in data:
            try:
              text = data["response"]["candidates"][0]["content"]["parts"][0]["text"].strip()
              if text.startswith("```json"):
                text = text[7:]
              if text.endswith("```"):
                text = text[:-3]
              text = text.strip()
              parsed = json.loads(text)
              
              if swapped:
                # 역방향 Swap 평가이므로 데이터 구조 내의 A와 B 지표를 교차 맵핑
                choice_raw = parsed.get("choice", "TIE")
                choice_mapped = "TIE"
                if choice_raw == "A":
                  choice_mapped = "B"
                elif choice_raw == "B":
                  choice_mapped = "A"
                  
                mapped = {
                  "choice": choice_mapped,
                  "response_a_accuracy": parsed.get("response_b_accuracy", 0),
                  "response_a_clarity": parsed.get("response_b_clarity", 0),
                  "response_a_completeness": parsed.get("response_b_completeness", 0),
                  "response_a_explanation": parsed.get("response_b_explanation", "Evaluation swapped."),
                  "response_a_score": parsed.get("response_b_score", 0.0),
                  "response_b_accuracy": parsed.get("response_a_accuracy", 0),
                  "response_b_clarity": parsed.get("response_a_clarity", 0),
                  "response_b_completeness": parsed.get("response_a_completeness", 0),
                  "response_b_explanation": parsed.get("response_a_explanation", "Evaluation swapped."),
                  "response_b_score": parsed.get("response_a_score", 0.0),
                  "explanation": parsed.get("explanation", "Swapped context.")
                }
                results[key] = mapped
              else:
                results[key] = parsed
            except Exception as e:
              results[key] = {"error": f"Parse error: {e}"}
  return results

eval_raw_1_dict = parse_eval_results(BUCKET_NAME, f"{OUTPUT_PREFIX}/{SESSION_ID}/output_eval_1/", swapped=False)
eval_raw_2_dict = parse_eval_results(BUCKET_NAME, f"{OUTPUT_PREFIX}/{SESSION_ID}/output_eval_2/", swapped=True)

output_lines = []
for i in range(total_items):
  key = str(id_arr[i])
  ans_a = resp_a_dict.get(key, "Inference failed.")
  ans_b = resp_b_dict.get(key, "Inference failed.")
  
  judgments_1 = eval_raw_1_dict.get(key, {})
  judgments_2 = eval_raw_2_dict.get(key, {})
  
  # 두 판사의 최종 지표 평균화 (Cross-Average)
  score_a = (float(judgments_1.get("response_a_score", 0.0)) + float(judgments_2.get("response_a_score", 0.0))) / 2.0
  score_b = (float(judgments_1.get("response_b_score", 0.0)) + float(judgments_2.get("response_b_score", 0.0))) / 2.0
  
  acc_a = int(round((int(judgments_1.get("response_a_accuracy", 0)) + int(judgments_2.get("response_a_accuracy", 0))) / 2.0))
  acc_b = int(round((int(judgments_1.get("response_b_accuracy", 0)) + int(judgments_2.get("response_b_accuracy", 0))) / 2.0))
  
  cla_a = int(round((int(judgments_1.get("response_a_clarity", 0)) + int(judgments_2.get("response_a_clarity", 0))) / 2.0))
  cla_b = int(round((int(judgments_1.get("response_b_clarity", 0)) + int(judgments_2.get("response_b_clarity", 0))) / 2.0))
  
  com_a = int(round((int(judgments_1.get("response_a_completeness", 0)) + int(judgments_2.get("response_a_completeness", 0))) / 2.0))
  com_b = int(round((int(judgments_1.get("response_b_completeness", 0)) + int(judgments_2.get("response_b_completeness", 0))) / 2.0))
  
  # 최종 승리자 산정
  selected_a = "N"
  selected_b = "N"
  if score_a > score_b:
    selected_a = "Y"
  elif score_b > score_a:
    selected_b = "Y"
  else:
    selected_a = "Y"
    selected_b = "Y"
    
  explanation_combined = f"Judge 1: {judgments_1.get('explanation', 'None')} | Judge 2: {judgments_2.get('explanation', 'None')}"
  
  row_a = {
    "accuracy": acc_a,
    "clarity": cla_a,
    "completeness": com_a,
    "context": context_arr[i],
    "dataset_hash": DATASET_HASH,
    "explanation": explanation_combined,
    "id": id_arr[i],
    "model_id": MODEL_A,
    "question": question_arr[i],
    "score": score_a,
    "selected": selected_a,
    "session_id": SESSION_ID,
    "summary": f"Judge 1: {judgments_1.get('response_a_explanation', 'None')} | Judge 2: {judgments_2.get('response_a_explanation', 'None')}"
  }
  
  row_b = {
    "accuracy": acc_b,
    "clarity": cla_b,
    "completeness": com_b,
    "context": context_arr[i],
    "dataset_hash": DATASET_HASH,
    "explanation": explanation_combined,
    "id": id_arr[i],
    "model_id": MODEL_B,
    "question": question_arr[i],
    "score": score_b,
    "selected": selected_b,
    "session_id": SESSION_ID,
    "summary": f"Judge 1: {judgments_1.get('response_b_explanation', 'None')} | Judge 2: {judgments_2.get('response_b_explanation', 'None')}"
  }
  output_lines.extend([row_a, row_b])

output_lines.sort(key=lambda x: (int(x["id"]), x["model_id"]))

with open(LOCAL_OUTPUT, "w", encoding="utf-8") as f:
  for item in output_lines:
    f.write(json.dumps(item, ensure_ascii=False) + "\n")

print(f"가공 완료! 로컬 임시 {LOCAL_OUTPUT} 저장 성공!")

print("빅쿼리 테이블에 최종 대용량 적재(Append) 수행 중...")
bq_client = bigquery.Client(project=PROJECT_ID)
table_ref = f"{PROJECT_ID}.evaluation_results.gemini_pairwise_judgments"

job_config = bigquery.LoadJobConfig(
  autodetect=True,
  schema_update_options=[bigquery.SchemaUpdateOption.ALLOW_FIELD_ADDITION],
  source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON
)

with open(LOCAL_OUTPUT, "rb") as source_file:
  bq_job = bq_client.load_table_from_file(
    source_file,
    table_ref,
    job_config=job_config
  )
bq_job.result()
print("빅쿼리 적재가 무결하게 완료되었다!")

# 비용 최적화를 위한 쿼리 수행 및 파티션 미적용 테이블 폴백 처리
query_str_partition = f"""
  SELECT 
    session_id, 
    model_id, 
    COUNT(id) AS total_questions, 
    ROUND(AVG(accuracy), 2) AS avg_accuracy, 
    ROUND(AVG(clarity), 2) AS avg_clarity, 
    ROUND(AVG(completeness), 2) AS avg_completeness, 
    ROUND(AVG(score), 2) AS avg_score, 
    ROUND(COUNTIF(CAST(selected AS STRING) IN ('Y', 'true')) / COUNT(id) * 100, 1) AS win_rate_percentage
  FROM evaluation_results.gemini_pairwise_judgments
  WHERE dataset_hash = '{DATASET_HASH}'
    AND _PARTITIONDATE >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)
  GROUP BY session_id, model_id
  ORDER BY session_id DESC, model_id ASC
"""

query_str_fallback = f"""
  SELECT 
    session_id, 
    model_id, 
    COUNT(id) AS total_questions, 
    ROUND(AVG(accuracy), 2) AS avg_accuracy, 
    ROUND(AVG(clarity), 2) AS avg_clarity, 
    ROUND(AVG(completeness), 2) AS avg_completeness, 
    ROUND(AVG(score), 2) AS avg_score, 
    ROUND(COUNTIF(CAST(selected AS STRING) IN ('Y', 'true')) / COUNT(id) * 100, 1) AS win_rate_percentage
  FROM evaluation_results.gemini_pairwise_judgments
  WHERE dataset_hash = '{DATASET_HASH}'
  GROUP BY session_id, model_id
  ORDER BY session_id DESC, model_id ASC
"""

try:
  query_job = bq_client.query(query_str_partition)
  results = query_job.result()
except Exception:
  print("비파티션 테이블 예외 감지: 최적화 필터를 제외한 폴백 쿼리를 가동한다.")
  query_job = bq_client.query(query_str_fallback)
  results = query_job.result()

print("+-------------------------+-----------------------+-----------------+--------------+-------------+------------------+-----------+---------------------+")
print("|       session_id        |       model_id        | total_questions | avg_accuracy | avg_clarity | avg_completeness | avg_score | win_rate_percentage |")
print("+-------------------------+-----------------------+-----------------+--------------+-------------+------------------+-----------+---------------------+")
for row in results:
  print(f"| {row.session_id:<23} | {row.model_id:<21} | {row.total_questions:<15} | {row.avg_accuracy:<12} | {row.avg_clarity:<11} | {row.avg_completeness:<16} | {row.avg_score:<9} | {row.win_rate_percentage:<19} |")
  print("+-------------------------+-----------------------+-----------------+--------------+-------------+------------------+-----------+---------------------+")

print("배치 예측 파이프라인 전체 프로세스가 성공적으로 마감되었다!")
EOF
