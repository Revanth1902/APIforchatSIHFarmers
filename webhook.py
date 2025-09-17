from flask import Flask, request, jsonify
import requests
import os
from deep_translator import GoogleTranslator

app = Flask(__name__)

# Detect language based on Malayalam unicode range
def detect_language(text):
    if any('\u0d00' <= ch <= '\u0d7f' for ch in text):  # Malayalam unicode range
        return "ml"
    return "en"

# Translate text
def translate_text(text, target_language="en"):
    try:
        return GoogleTranslator(source='auto', target=target_language).translate(text)
    except Exception as e:
        print("Translation error:", e)
        return text

# Call Gemini API
def call_gemini_api(user_query):
    api_key = os.getenv("GEMINI_API_KEY")
    # Use latest Gemini model
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"

    headers = {"Content-Type": "application/json"}
    data = {
        "contents": [
            {
                "parts": [{"text": user_query}]
            }
        ]
    }

    response = requests.post(url, headers=headers, json=data)

    print("Gemini response status:", response.status_code)
    print("Gemini response body:", response.text)

    if response.status_code == 200:
        return response.json()["candidates"][0]["content"]["parts"][0]["text"]
    else:
        return "Sorry, I couldn't fetch a response from Gemini."

@app.route('/webhook', methods=['POST'])
def webhook():
    req = request.get_json(force=True)
    print("Received request:", req)

    query_text = req.get("queryResult", {}).get("queryText", "")
    if not query_text:
        return jsonify({"fulfillmentText": "I didn’t get any input."})

    # Detect input language
    detected_lang = detect_language(query_text)

    # Translate Malayalam → English
    if detected_lang == "ml":
        translated_query = translate_text(query_text, target_language="en")
    else:
        translated_query = query_text

    # Get response from Gemini
    gemini_response = call_gemini_api(translated_query)

    # Translate back English → Malayalam if needed
    if detected_lang == "ml":
        gemini_response = translate_text(gemini_response, target_language="ml")

    #  Proper response structure + UTF-8
    response = jsonify({
        "fulfillmentText": gemini_response,
        "fulfillmentMessages": [
            {"text": {"text": [gemini_response]}}
        ]
    })
    response.headers["Content-Type"] = "application/json; charset=utf-8"
    return response



if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)
