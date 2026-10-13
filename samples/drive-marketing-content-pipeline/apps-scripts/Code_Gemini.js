/**
 * Copyright 2026 Google LLC. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 *
 * Drive Marketing Content Pipeline
 * [모듈 2] Gemini REST API 클라이언트 엔진 (구글 계정 OAuth 2.0 자동 로그인 기반 Keyless 인증)
 */

/**
 * Gemini API 인증 헤더 조회 (현재 구글 로그인 계정의 OAuth 2.0 Access Token 기반 Keyless 인증)
 * 비개발자 마케터가 별도 API Key를 발급받을 필요 없이 구글 로그인 세션으로 자동 인증된다.
 */
function getGeminiAuthHeaders() {
  try {
    var oauthToken = ScriptApp.getOAuthToken();
    if (oauthToken) {
      return {
        "Authorization": "Bearer " + oauthToken
      };
    }
  } catch (oauthErr) {
    Logger.log("OAuth 토큰 취득 예외: " + oauthErr);
  }

  throw new Error(
    "구글 계정 인증 정보를 확인할 수 없습니다. 구글 스프레드시트의 계정 권한 승인 창에서 [허용]을 클릭하십시오."
  );
}

/**
 * Gemini 텍스트 생성 API 호출 (System Instruction 및 User Content)
 */
function callGemini(systemInstruction, userContent, modelOverride, maxTokensOverride) {
  var headers = getGeminiAuthHeaders();
  var targetModel = modelOverride || CONFIG.MODEL_GENERATOR || CONFIG.GEMINI_MODEL || "gemini-3.8-flash";
  var endpoint = CONFIG.BASE_URL + "/" + targetModel + ":generateContent";
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
    headers: headers,
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
  var headers = getGeminiAuthHeaders();
  var targetModel = modelOverride || CONFIG.MODEL_GENERATOR || "gemini-3.8-flash";
  var endpoint = CONFIG.BASE_URL + "/" + targetModel + ":generateContent";

  var mimeType = mediaBlob.getContentType();
  var base64Data = Utilities.base64Encode(mediaBlob.getBytes());

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
    headers: headers,
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
 * Gemini Imagen / Flash Image 생성 API 호출 (상업용 광고 비주얼 시안 생성)
 */
function callGeminiImage(prompt, aspectRatio) {
  try {
    var headers = getGeminiAuthHeaders();
    var imgModel = CONFIG.IMAGE_MODEL_NAME || "gemini-2.5-flash-image";
    var endpoint = CONFIG.BASE_URL + "/" + imgModel + ":predict";
    var ratio = aspectRatio || "1:1";

    var payload = {
      instances: [
        { prompt: prompt + ", high quality commercial advertising photography, professional studio lighting, 8k resolution" }
      ],
      parameters: {
        sampleCount: 1,
        aspectRatio: ratio
      }
    };

    var options = {
      method: "post",
      contentType: "application/json",
      headers: headers,
      payload: JSON.stringify(payload),
      muteHttpExceptions: true
    };

    var response = UrlFetchApp.fetch(endpoint, options);
    if (response.getResponseCode() === 200) {
      var result = JSON.parse(response.getContentText());
      if (result.predictions && result.predictions.length > 0 && result.predictions[0].bytesBase64Encoded) {
        return result.predictions[0].bytesBase64Encoded;
      }
    } else {
      Logger.log("Gemini 이미지 생성 실패 (" + response.getResponseCode() + "): " + response.getContentText());
    }
  } catch (err) {
    Logger.log("Gemini 이미지 생성 네트워크 예외: " + err);
  }
  return null;
}
