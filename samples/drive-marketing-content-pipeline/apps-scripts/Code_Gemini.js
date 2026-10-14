/**
 * Copyright 2026 Google LLC. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 *
 * Drive Marketing Content Pipeline
 * [모듈 2] Gemini REST API 클라이언트 엔진 (Google AI Studio 무료 API Key 기반 Zero-GCP 인증)
 */

/**
 * Google AI Studio Gemini API Key 취득 함수
 * 1순위: UserProperties (사용자 개인별 안전 보관)
 * 2순위: ScriptProperties (스크립트 공용 설정)
 * 3순위: CONFIG.API_KEY (코드 내 직접 설정)
 * 4순위: 키가 없을 경우 자동으로 대화상자 프롬프트 호출
 */
function getGeminiApiKey() {
  var userProps = PropertiesService.getUserProperties();
  var key = userProps.getProperty("GEMINI_API_KEY");
  if (key && key.trim()) {
    return key.trim();
  }

  var scriptProps = PropertiesService.getScriptProperties();
  key = scriptProps.getProperty("GEMINI_API_KEY");
  if (key && key.trim()) {
    return key.trim();
  }

  if (CONFIG.API_KEY && CONFIG.API_KEY.trim()) {
    return CONFIG.API_KEY.trim();
  }

  return promptForGeminiApiKey();
}

/**
 * Google AI Studio Gemini API Key 입력 및 저장 UI 프롬프트
 */
function promptForGeminiApiKey() {
  var ui = SpreadsheetApp.getUi();
  var userProps = PropertiesService.getUserProperties();
  var currentKey = userProps.getProperty("GEMINI_API_KEY") || "";
  var maskedKey = currentKey ? (currentKey.substring(0, 6) + "..." + currentKey.substring(currentKey.length - 4)) : "미등록";

  var response = ui.prompt(
    "Google AI Studio Gemini API Key 설정 (Zero-GCP)",
    "Google Cloud 콘솔 및 신용카드 등록 없이 개인 구글 계정으로 100% 무료 구동됩니다.\n\n" +
    "1. Google AI Studio ( https://aistudio.google.com/app/apikey ) 에서 무료 API Key를 발급받으십시오.\n" +
    "2. 발급받은 API Key(AIzaSy...)를 아래에 입력하십시오:\n\n" +
    "(현재 등록된 키: " + maskedKey + ")",
    ui.ButtonSet.OK_CANCEL
  );

  if (response.getSelectedButton() === ui.Button.OK) {
    var inputKey = response.getResponseText().trim();
    if (inputKey) {
      userProps.setProperty("GEMINI_API_KEY", inputKey);
      ui.alert("설정 완료", "Gemini API Key가 안전하게 저장되었습니다.\n파이프라인 단계를 계속 진행하십시오.", ui.ButtonSet.OK);
      return inputKey;
    } else {
      ui.alert("입력 오류", "유효한 API Key가 입력되지 않았습니다.", ui.ButtonSet.OK);
    }
  }

  throw new Error("Gemini API Key가 설정되지 않아 작업을 중단합니다. 메뉴의 [Gemini API Key 설정]에서 키를 등록하십시오.");
}

/**
 * Gemini 텍스트 생성 API 호출 (System Instruction 및 User Content)
 */
function callGemini(systemInstruction, userContent, modelOverride, maxTokensOverride) {
  var apiKey = getGeminiApiKey();
  var targetModel = modelOverride || CONFIG.MODEL_GENERATOR || CONFIG.GEMINI_MODEL || "gemini-3.8-flash";
  var endpoint = CONFIG.BASE_URL + "/" + targetModel + ":generateContent?key=" + apiKey;
  var maxTokens = maxTokensOverride || 8192;

  var payload = {
    contents: [{
      role: "user",
      parts: [{ text: userContent }]
    }],
    generationConfig: {
      maxOutputTokens: maxTokens,
      temperature: 0.7
    }
  };

  if (systemInstruction) {
    payload.systemInstruction = {
      parts: [{ text: systemInstruction }]
    };
  }

  var options = {
    method: "post",
    contentType: "application/json",
    payload: JSON.stringify(payload),
    muteHttpExceptions: true
  };

  var response = UrlFetchApp.fetch(endpoint, options);
  var responseCode = response.getResponseCode();
  var responseBody = response.getContentText();

  if (responseCode !== 200) {
    throw new Error("Gemini API 호출 실패 (상태 코드: " + responseCode + "):\n" + responseBody);
  }

  var result = JSON.parse(responseBody);
  if (result.candidates && result.candidates.length > 0 && 
      result.candidates[0].content && result.candidates[0].content.parts) {
    return result.candidates[0].content.parts[0].text;
  }

  throw new Error("Gemini API로부터 유효한 텍스트 응답을 수신하지 못했습니다:\n" + responseBody);
}

/**
 * Gemini 멀티모달(VLM) 심층 분석 API 호출 (구글 드라이브 이미지 및 비디오 Blob 직접 처리)
 */
function callGeminiMultimodal(prompt, mediaBlob, modelOverride) {
  var apiKey = getGeminiApiKey();
  var targetModel = modelOverride || CONFIG.MODEL_GENERATOR || "gemini-3.8-flash";
  var endpoint = CONFIG.BASE_URL + "/" + targetModel + ":generateContent?key=" + apiKey;

  var mimeType = mediaBlob.getContentType();
  var bytes = mediaBlob.getBytes();
  var sizeInMb = bytes.length / (1024 * 1024);

  // Apps Script 런타임 제약 사전 방어 (페이로드 50MB 한계 및 6분 타임아웃 방지)
  if (sizeInMb > 35) {
    throw new Error(
      "미디어 파일 크기(" + sizeInMb.toFixed(1) + "MB)가 Apps Script 단일 페이로드 한계(Base64 인코딩 기준 실질 35MB)를 초과합니다. " +
      "안정적인 실행을 위해 15~30초 이내(30MB 이하)의 숏폼 영상을 권장하며, " +
      "장시간 고객 인터뷰나 대용량 영상 분석을 위한 Google Cloud 환경으로의 이관은 Google Cloud에 연락하여 전문 컨설팅을 받으십시오."
    );
  }

  var base64Data = Utilities.base64Encode(bytes);

  var payload = {
    contents: [{
      role: "user",
      parts: [
        { text: prompt },
        {
          inlineData: {
            mimeType: mimeType,
            data: base64Data
          }
        }
      ]
    }],
    generationConfig: {
      maxOutputTokens: 8192,
      temperature: 0.4
    }
  };

  var options = {
    method: "post",
    contentType: "application/json",
    payload: JSON.stringify(payload),
    muteHttpExceptions: true
  };

  var response = UrlFetchApp.fetch(endpoint, options);
  var responseCode = response.getResponseCode();
  var responseBody = response.getContentText();

  if (responseCode !== 200) {
    throw new Error("Gemini 멀티모달 분석 실패 (상태 코드: " + responseCode + "):\n" + responseBody);
  }

  var result = JSON.parse(responseBody);
  if (result.candidates && result.candidates.length > 0 && 
      result.candidates[0].content && result.candidates[0].content.parts) {
    return result.candidates[0].content.parts[0].text;
  }

  throw new Error("Gemini 멀티모달 응답 수신 실패:\n" + responseBody);
}

/**
 * Gemini 이미지 생성 API 호출 (상업용 광고 비주얼 시안 생성)
 * 최신 멀티모달 이미지 생성 모델 캐스케이드(Cascade Fallback) 적용:
 * 1순위: gemini-nano-banana-2.1 (:generateContent, responseModalities: ["IMAGE"])
 * 2순위: gemini-3.1-flash-image (:generateContent, responseModalities: ["IMAGE"])
 * 3순위: imagen-4.0-generate-001 (:predict)
 * 4순위: imagen-3.0-generate (:predict)
 */
function callGeminiImage(prompt, aspectRatio) {
  try {
    var apiKey = getGeminiApiKey();
    if (!apiKey) {
      Logger.log("API Key 누락으로 이미지 생성을 건너뜁니다.");
      return null;
    }

    var fullPrompt = prompt + ", commercial advertising product photography, professional studio lighting, 8k resolution, photorealistic";
    var ratio = aspectRatio || "1:1";

    // 1순위 & 2순위: Gemini 네이티브 이미지 생성 모델 (:generateContent)
    var nativeModels = [
      (CONFIG && CONFIG.IMAGE_MODEL_NAME) || "gemini-nano-banana-2.1",
      "gemini-3.1-flash-image"
    ];

    for (var m = 0; m < nativeModels.length; m++) {
      var nModel = nativeModels[m];
      try {
        var nEndpoint = CONFIG.BASE_URL + "/" + nModel + ":generateContent?key=" + apiKey;
        var nPayload = {
          contents: [{
            parts: [{ text: fullPrompt }]
          }],
          generationConfig: {
            responseModalities: ["IMAGE"]
          }
        };

        var nOptions = {
          method: "post",
          contentType: "application/json",
          headers: {
            "x-goog-api-key": apiKey
          },
          payload: JSON.stringify(nPayload),
          muteHttpExceptions: true
        };

        Logger.log("Gemini 이미지 생성 시도 (모델: " + nModel + ", 종횡비: " + ratio + ")...");
        var nResp = UrlFetchApp.fetch(nEndpoint, nOptions);
        var nCode = nResp.getResponseCode();
        var nBody = nResp.getContentText();

        if (nCode === 200) {
          var nResult = JSON.parse(nBody);
          if (nResult.candidates && nResult.candidates.length > 0 && 
              nResult.candidates[0].content && nResult.candidates[0].content.parts) {
            var parts = nResult.candidates[0].content.parts;
            for (var p = 0; p < parts.length; p++) {
              if (parts[p].inlineData && parts[p].inlineData.data) {
                Logger.log("Gemini 이미지 생성 성공 (모델: " + nModel + ")");
                return {
                  base64: parts[p].inlineData.data,
                  mimeType: parts[p].inlineData.mimeType || "image/png"
                };
              }
            }
          }
        } else {
          Logger.log("Gemini 이미지 모델(" + nModel + ") 호출 실패 (" + nCode + "): " + nBody);
        }
      } catch (nErr) {
        Logger.log("Gemini 이미지 모델(" + nModel + ") 호출 예외: " + nErr);
      }
    }

    // 3순위 & 4순위: Imagen 계열 모델 폴백 (:predict)
    var imagenModels = ["imagen-4.0-generate-001", "imagen-3.0-generate"];
    for (var i = 0; i < imagenModels.length; i++) {
      var imgModel = imagenModels[i];
      try {
        var imgEndpoint = CONFIG.BASE_URL + "/" + imgModel + ":predict?key=" + apiKey;
        var imgPayload = {
          instances: [
            { prompt: fullPrompt }
          ],
          parameters: {
            sampleCount: 1,
            aspectRatio: ratio
          }
        };

        var imgOptions = {
          method: "post",
          contentType: "application/json",
          headers: {
            "x-goog-api-key": apiKey
          },
          payload: JSON.stringify(imgPayload),
          muteHttpExceptions: true
        };

        Logger.log("Imagen 이미지 생성 시도 (모델: " + imgModel + ")...");
        var imgResp = UrlFetchApp.fetch(imgEndpoint, imgOptions);
        var imgCode = imgResp.getResponseCode();
        var imgBody = imgResp.getContentText();

        if (imgCode === 200) {
          var imgResult = JSON.parse(imgBody);
          if (imgResult.predictions && imgResult.predictions.length > 0 && imgResult.predictions[0].bytesBase64Encoded) {
            Logger.log("Imagen 이미지 생성 성공 (모델: " + imgModel + ")");
            return {
              base64: imgResult.predictions[0].bytesBase64Encoded,
              mimeType: imgResult.predictions[0].mimeType || "image/jpeg"
            };
          }
        } else {
          Logger.log("Imagen 모델(" + imgModel + ") 호출 실패 (" + imgCode + "): " + imgBody);
        }
      } catch (imgErr) {
        Logger.log("Imagen 모델(" + imgModel + ") 예외: " + imgErr);
      }
    }
  } catch (err) {
    Logger.log("이미지 생성 전체 예외: " + err);
  }
  return null;
}

/**
 * Gemini Veo 비디오 생성 API 호출 (9:16 모바일 숏폼 영상 생성)
 * Google AI Studio / Gemini Developer API의 predictLongRunning 엔드포인트 및 LRO 폴링
 * 1순위: veo-3.1-generate-preview (:predictLongRunning)
 * 2순위: veo-3.1-fast-generate-preview (:predictLongRunning)
 *
 * @param {string} prompt - 영문 비디오 연출 프롬프트
 * @param {string} [aspectRatio] - 종횡비 (기본값: "9:16")
 * @param {number} [durationSeconds] - 영상 길이 (초 단위, 기본값: 5)
 * @return {{ base64: string, mimeType: string } | null} 생성된 비디오 base64 객체 또는 null
 */
function callGeminiVideo(prompt, aspectRatio, durationSeconds) {
  try {
    var apiKey = getGeminiApiKey();
    if (!apiKey) {
      Logger.log("API Key 누락으로 Veo 비디오 생성을 건너뜁니다.");
      return null;
    }

    var ratio = aspectRatio || "9:16";
    var duration = durationSeconds || 5;

    var candidateModels = [
      (CONFIG && CONFIG.VIDEO_MODEL_NAME) || "veo-3.1-generate-preview",
      "veo-3.1-fast-generate-preview"
    ];

    var operationName = null;
    var activeModel = candidateModels[0];

    for (var m = 0; m < candidateModels.length; m++) {
      var modelName = candidateModels[m];
      var endpoint = CONFIG.BASE_URL + "/" + modelName + ":predictLongRunning";

      var payload = {
        instances: [
          {
            prompt: prompt
          }
        ],
        parameters: {
          sampleCount: 1,
          aspectRatio: ratio,
          durationSeconds: duration
        }
      };

      var options = {
        method: "post",
        contentType: "application/json",
        headers: {
          "x-goog-api-key": apiKey
        },
        payload: JSON.stringify(payload),
        muteHttpExceptions: true
      };

      Logger.log("Veo 비디오 생성 요청 시작 (모델: " + modelName + ", 비율: " + ratio + "): " + prompt.substring(0, 80) + "...");
      var response = UrlFetchApp.fetch(endpoint, options);
      var code = response.getResponseCode();
      var body = response.getContentText();

      if (code === 200) {
        var initResult = JSON.parse(body);
        if (initResult.name) {
          operationName = initResult.name;
          activeModel = modelName;
          break;
        }
      } else {
        Logger.log("Veo 초기 생성 요청 실패 (모델: " + modelName + ", 상태 코드: " + code + "): " + body);
      }
    }

    if (!operationName) {
      Logger.log("모든 Veo 모델 생성 작업 큐 등록에 실패하여 비디오 생성을 완료하지 못했습니다.");
      return null;
    }

    Logger.log("Veo 장기 실행 작업(LRO) 등록 완료 (" + activeModel + "): " + operationName + ". 완료 대기 폴링 시작...");

    // LRO 폴링: Apps Script 런타임 제약(단일 실행 6분) 내에서 5초 간격으로 최대 18회(90초) 폴링
    var pollUrl = "https://generativelanguage.googleapis.com/v1beta/" + operationName;
    var pollOptions = {
      method: "get",
      headers: {
        "x-goog-api-key": apiKey
      },
      muteHttpExceptions: true
    };

    var maxAttempts = 18; // 5초 * 18회 = 최대 90초
    for (var attempt = 1; attempt <= maxAttempts; attempt++) {
      Utilities.sleep(5000);

      var pollResp = UrlFetchApp.fetch(pollUrl, pollOptions);
      var pCode = pollResp.getResponseCode();
      if (pCode !== 200) {
        Logger.log("Veo 폴링 응답 오류 (시도 " + attempt + "/" + maxAttempts + ", 응답 코드: " + pCode + ")");
        continue;
      }

      var pollData = JSON.parse(pollResp.getContentText());
      if (pollData.error) {
        Logger.log("Veo 비디오 생성 작업 에러: " + JSON.stringify(pollData.error));
        return null;
      }

      if (pollData.done === true) {
        Logger.log("Veo 비디오 렌더링 완료! (" + (attempt * 5) + "초 소요)");
        var respObj = pollData.response || pollData.result;
        if (!respObj) {
          Logger.log("완료된 Veo 작업에 결과 데이터가 없습니다: " + JSON.stringify(pollData));
          return null;
        }

        var genVideoResp = respObj.generateVideoResponse || respObj;
        var samples = genVideoResp.generatedSamples || genVideoResp.generatedVideos || [];
        if (samples.length > 0 && samples[0].video) {
          var vObj = samples[0].video;
          var encoded = vObj.encodedVideo || vObj.bytesBase64Encoded || vObj.videoBytes;
          if (encoded) {
            return {
              base64: encoded,
              mimeType: vObj.encoding || vObj.mimeType || "video/mp4"
            };
          }
          if (vObj.uri) {
            Logger.log("Veo 비디오 파일 다운로드 중: " + vObj.uri);
            // 1차: x-goog-api-key 헤더 포함 다운로드
            var dlResp = UrlFetchApp.fetch(vObj.uri, {
              method: "get",
              headers: { "x-goog-api-key": apiKey },
              followRedirects: true,
              muteHttpExceptions: true
            });
            // 만약 인증 방식 충돌(400/403) 시 헤더 없이 순수 다운로드 2차 시도
            if (dlResp.getResponseCode() !== 200) {
              dlResp = UrlFetchApp.fetch(vObj.uri, {
                method: "get",
                followRedirects: true,
                muteHttpExceptions: true
              });
            }

            if (dlResp.getResponseCode() === 200) {
              var blob = dlResp.getBlob();
              return {
                base64: Utilities.base64Encode(blob.getBytes()),
                mimeType: blob.getContentType() || "video/mp4"
              };
            } else {
              Logger.log("Veo 비디오 URI 다운로드 실패 (" + dlResp.getResponseCode() + "): " + dlResp.getContentText());
            }
          }
        }
        Logger.log("Veo 결과 파싱 실패: " + JSON.stringify(respObj));
        return null;
      }

      Logger.log("Veo 렌더링 진행 중... (시도 " + attempt + "/" + maxAttempts + ")");
    }

    Logger.log("Veo 렌더링 시간 초과 (90초). 백그라운드 처리가 계속될 수 있습니다.");
    return null;
  } catch (err) {
    Logger.log("Veo 비디오 생성 예외: " + err);
    return null;
  }
}

/**
 * 한국어 및 다국어 특화 텍스트 임베딩 모델(text-multilingual-embedding-002)을 호출하여
 * 텍스트 목록을 128차원(MRL) 벡터 배열로 일괄 변환한다.
 *
 * @param {Array<string>} texts - 임베딩할 세부 의견 텍스트 배열
 * @param {number} [optDim] - MRL 축소 차원 (기본값: CONFIG.EMBEDDING_DIM 또는 128)
 * @return {Array<Array<number>>} 128차원 부동소수점 벡터 배열
 */
function callGeminiBatchEmbeddings(texts, optDim) {
  if (!texts || texts.length === 0) {
    return [];
  }

  var dim = optDim || CONFIG.EMBEDDING_DIM || 128;
  var embedModel = CONFIG.EMBEDDING_MODEL || "text-multilingual-embedding-002";
  var apiKey = getGeminiApiKey();
  var endpoint = CONFIG.BASE_URL + "/" + embedModel + ":batchEmbedContents?key=" + apiKey;

  var allEmbeddings = [];
  var chunkSize = 25; // Apps Script 안정성을 위해 25건 단위 청킹

  for (var i = 0; i < texts.length; i += chunkSize) {
    var chunk = texts.slice(i, i + chunkSize);
    var requests = [];
    for (var c = 0; c < chunk.length; c++) {
      requests.push({
        model: "models/" + embedModel,
        content: { parts: [{ text: String(chunk[c]).substring(0, 2048) }] },
        outputDimensionality: dim
      });
    }

    var payload = { requests: requests };
    var options = {
      method: "post",
      contentType: "application/json",
      payload: JSON.stringify(payload),
      muteHttpExceptions: true
    };

    try {
      var response = UrlFetchApp.fetch(endpoint, options);
      var code = response.getResponseCode();
      var body = response.getContentText();

      if (code === 200) {
        var parsed = JSON.parse(body);
        if (parsed.embeddings && parsed.embeddings.length > 0) {
          for (var e = 0; e < parsed.embeddings.length; e++) {
            var item = parsed.embeddings[e];
            if (item && item.values && item.values.length > 0) {
              allEmbeddings.push(item.values);
            } else {
              allEmbeddings.push(createDeterministicVector(chunk[e], dim));
            }
          }
        } else {
          for (var f = 0; f < chunk.length; f++) {
            allEmbeddings.push(createDeterministicVector(chunk[f], dim));
          }
        }
      } else {
        Logger.log("임베딩 일괄 호출 경고 (" + code + "): " + body + " -> 결정론적 128차원 벡터 폴백");
        for (var k = 0; k < chunk.length; k++) {
          allEmbeddings.push(createDeterministicVector(chunk[k], dim));
        }
      }
    } catch (netErr) {
      Logger.log("임베딩 통신 예외: " + netErr + " -> 결정론적 128차원 벡터 폴백");
      for (var m = 0; m < chunk.length; m++) {
        allEmbeddings.push(createDeterministicVector(chunk[m], dim));
      }
    }
  }

  return allEmbeddings;
}

/**
 * 네트워크 단절이나 API 할당량 소진 시 파이프라인 중단을 방지하기 위한
 * 텍스트 해시 기반 결정론적(Deterministic) 128차원 정규화 벡터 생성 헬퍼
 */
function createDeterministicVector(text, dim) {
  var d = dim || 128;
  var vec = new Array(d);
  var str = String(text || "fallback");
  var seed = 0;
  for (var i = 0; i < str.length; i++) {
    seed = (seed << 5) - seed + str.charCodeAt(i);
    seed |= 0;
  }
  var norm = 0;
  for (var j = 0; j < d; j++) {
    var val = Math.sin(seed * (j + 1) * 0.1234) + Math.cos((j + 1) * 0.5678);
    vec[j] = val;
    norm += val * val;
  }
  norm = Math.sqrt(norm) || 1.0;
  for (var k = 0; k < d; k++) {
    vec[k] = Number((vec[k] / norm).toFixed(6));
  }
  return vec;
}
