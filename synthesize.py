#!/usr/bin/env python3
# coding: utf-8
"""
Personal Voice Text-to-Speech Script

Reads text from a Markdown file and synthesizes audio using an Azure Personal Voice.
The personal voice must already exist in your Azure Speech Service subscription.

Supports both:
  - Trial personal voices (created via Speech Studio trial flow)
  - Full personal voices (created via REST API with consent + audio)

Usage:
    python synthesize.py                          # uses input.md by default
    python synthesize.py my_text.md                # uses a custom markdown file
    python synthesize.py -o demo                   # output as demo.wav / demo.mp3
    python synthesize.py my_text.md -o recording   # custom input + output name
"""

import argparse
import os
import sys
import re

import requests
from dotenv import load_dotenv


def load_config():
    """Load configuration from .env file."""
    load_dotenv()

    required = ["SPEECH_KEY", "SPEECH_REGION", "SPEAKER_PROFILE_ID"]
    config = {}
    for key in required:
        value = os.getenv(key)
        if not value or value.startswith("your_"):
            print(f"ERROR: '{key}' is not set in .env file. Please fill in your actual value.")
            sys.exit(1)
        config[key] = value

    config["SPEECH_LANGUAGE"] = os.getenv("SPEECH_LANGUAGE", "en-US")
    config["SPEECH_STYLE"] = os.getenv("SPEECH_STYLE", "Cheerful")
    config["OUTPUT_FORMAT"] = os.getenv("OUTPUT_FORMAT", "wav").lower()
    config["OUTPUT_FILENAME"] = os.getenv("OUTPUT_FILENAME", "output")

    return config


def read_markdown(file_path: str) -> str:
    """
    Read a Markdown file and extract plain text suitable for TTS.
    Strips Markdown headings (#), bold/italic markers, links, and images.
    """
    if not os.path.isfile(file_path):
        print(f"ERROR: Input file '{file_path}' not found.")
        sys.exit(1)

    with open(file_path, "r", encoding="utf-8") as f:
        text = f.read()

    # Remove images ![alt](url)
    text = re.sub(r"!\[.*?\]\(.*?\)", "", text)
    # Convert links [text](url) -> text
    text = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", text)
    # Remove heading markers
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
    # Remove bold/italic markers
    text = re.sub(r"\*{1,3}(.*?)\*{1,3}", r"\1", text)
    text = re.sub(r"_{1,3}(.*?)_{1,3}", r"\1", text)
    # Remove inline code
    text = re.sub(r"`([^`]+)`", r"\1", text)
    # Remove code blocks
    text = re.sub(r"```[\s\S]*?```", "", text)
    # Remove horizontal rules
    text = re.sub(r"^[-*_]{3,}\s*$", "", text, flags=re.MULTILINE)
    # Collapse multiple blank lines into one
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def synthesize_trial(config: dict, text: str) -> None:
    """
    Synthesize text using the trial Personal Voice REST API.
    This is used for voices created through Speech Studio's trial flow.
    """
    region = config["SPEECH_REGION"]
    key = config["SPEECH_KEY"]
    speaker_id = config["SPEAKER_PROFILE_ID"]
    language = config["SPEECH_LANGUAGE"]
    output_file = f"{config['OUTPUT_FILENAME']}.{config['OUTPUT_FORMAT']}"

    synth_url = (
        f"https://{region}.api.cognitive.microsoft.com"
        f"/customvoice/trial/synthesis?api-version=2023-07-01-preview"
    )
    model_url = (
        f"https://{region}.api.cognitive.microsoft.com"
        f"/customvoice/trial/zeroshots/{speaker_id}?api-version=2023-07-01-preview"
    )

    headers = {
        "Ocp-Apim-Subscription-Key": key,
        "Content-Type": "application/json",
    }

    # scriptOrder varies by locale in the trial API
    # Known values from Speech Studio: en-US=11, es-ES=13
    # Use a lookup with a fallback
    SCRIPT_ORDER_BY_LOCALE = {
        "en-US": 11, "en-GB": 11, "en-AU": 11, "en-IN": 11,
        "es-ES": 13, "es-MX": 13,
        "fr-FR": 12, "de-DE": 12, "it-IT": 12,
        "ja-JP": 14, "ko-KR": 14, "zh-CN": 14,
        "pt-BR": 13,
    }
    script_order = SCRIPT_ORDER_BY_LOCALE.get(language, 11)

    body = {
        "model": model_url,
        "locale": language,
        "scriptOrder": script_order,
        "text": text,
        "baseModelName": "DragonLatestNeural",
    }

    print("Synthesizing with Personal Voice (trial API)...")
    print(f"  Region:             {region}")
    print(f"  Language:           {language}")
    print(f"  Speaker Profile ID: {speaker_id}")
    print(f"  Output file:        {output_file}")
    print(f"  Text length:        {len(text)} characters")
    print()

    response = requests.post(synth_url, headers=headers, json=body, timeout=120)

    if response.status_code == 200 and "audio" in response.headers.get("Content-Type", ""):
        with open(output_file, "wb") as f:
            f.write(response.content)
        size_kb = len(response.content) / 1024
        print(f"SUCCESS: Audio saved to '{output_file}' ({size_kb:.1f} KB)")
    else:
        print(f"ERROR: Synthesis failed (HTTP {response.status_code})")
        try:
            err = response.json()
            msg = err.get("error", {}).get("message", response.text[:300])
            inner = err.get("error", {}).get("innererror", {}).get("message", "")
            print(f"  Message: {msg}")
            if inner:
                print(f"  Detail:  {inner}")
        except Exception:
            print(f"  Response: {response.text[:300]}")
        sys.exit(1)


def synthesize_sdk(config: dict, text: str) -> None:
    """
    Synthesize text using the Speech SDK (for non-trial personal voices).
    Requires a proper speakerProfileId from the Custom Voice REST API.
    """
    try:
        import azure.cognitiveservices.speech as speechsdk
    except ImportError:
        print("Azure Speech SDK not found. Install with: pip install azure-cognitiveservices-speech")
        sys.exit(1)

    import html as _html

    speech_config = speechsdk.SpeechConfig(
        subscription=config["SPEECH_KEY"],
        region=config["SPEECH_REGION"]
    )

    if config["OUTPUT_FORMAT"] == "mp3":
        speech_config.set_speech_synthesis_output_format(
            speechsdk.SpeechSynthesisOutputFormat.Audio24Khz160KBitRateMonoMp3
        )
        output_file = f"{config['OUTPUT_FILENAME']}.mp3"
    else:
        speech_config.set_speech_synthesis_output_format(
            speechsdk.SpeechSynthesisOutputFormat.Riff24Khz16BitMonoPcm
        )
        output_file = f"{config['OUTPUT_FILENAME']}.wav"

    file_config = speechsdk.audio.AudioOutputConfig(filename=output_file)
    synthesizer = speechsdk.SpeechSynthesizer(
        speech_config=speech_config,
        audio_config=file_config
    )

    lang = config["SPEECH_LANGUAGE"]
    spid = config["SPEAKER_PROFILE_ID"]
    style = config.get("SPEECH_STYLE", "Cheerful")
    escaped_text = _html.escape(text)

    # Build the inner content with optional prosody adjustments
    PROSODY_PRESETS = {
        "Cheerful":    {"rate": "+8%",  "pitch": "+5%"},
        "Excited":     {"rate": "+12%", "pitch": "+8%"},
        "Friendly":    {"rate": "+5%",  "pitch": "+3%"},
        "Enthusiastic":{"rate": "+10%", "pitch": "+6%"},
    }
    prosody = PROSODY_PRESETS.get(style)
    if prosody:
        inner = (f"<prosody rate='{prosody['rate']}' pitch='{prosody['pitch']}'>"
                 f"<lang xml:lang='{lang}'>{escaped_text}</lang>"
                 f"</prosody>")
    else:
        inner = f"<lang xml:lang='{lang}'>{escaped_text}</lang>"

    ssml = (
        f"<speak version='1.0' xml:lang='{lang}' "
        f"xmlns='http://www.w3.org/2001/10/synthesis' "
        f"xmlns:mstts='http://www.w3.org/2001/mstts'>"
        f"<voice name='DragonLatestNeural'>"
        f"<mstts:ttsembedding speakerProfileId='{_html.escape(spid)}'/>"
        f"<mstts:express-as style='{_html.escape(style)}'>"
        f"{inner}"
        f"</mstts:express-as>"
        f"</voice>"
        f"</speak>"
    )

    print("Synthesizing with Personal Voice (SDK)...")
    print(f"  Region:             {config['SPEECH_REGION']}")
    print(f"  Language:           {lang}")
    print(f"  Speaker Profile ID: {spid}")
    print(f"  Style:              {style}")
    print(f"  Output file:        {output_file}")
    print(f"  Text length:        {len(text)} characters")
    print()

    result = synthesizer.speak_ssml_async(ssml).get()

    if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
        print(f"SUCCESS: Audio saved to '{output_file}'")
        print(f"  Result ID: {result.result_id}")
    elif result.reason == speechsdk.ResultReason.Canceled:
        cancellation = result.cancellation_details
        print(f"CANCELED: {cancellation.reason}")
        if cancellation.reason == speechsdk.CancellationReason.Error:
            print(f"  Error details: {cancellation.error_details}")
        sys.exit(1)


def is_trial_voice(config: dict) -> bool:
    """Check if the speaker profile ID corresponds to a trial voice."""
    region = config["SPEECH_REGION"]
    key = config["SPEECH_KEY"]
    speaker_id = config["SPEAKER_PROFILE_ID"]

    url = (
        f"https://{region}.api.cognitive.microsoft.com"
        f"/customvoice/trial/zeroshots/{speaker_id}?api-version=2023-07-01-preview"
    )
    headers = {"Ocp-Apim-Subscription-Key": key}
    try:
        r = requests.get(url, headers=headers, timeout=10)
        return r.status_code == 200
    except Exception:
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Synthesize audio from a Markdown file using an Azure Personal Voice."
    )
    parser.add_argument(
        "input", nargs="?",
        default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "input.md"),
        help="Path to the input Markdown file (default: input.md)"
    )
    parser.add_argument(
        "-o", "--output",
        default=None,
        help="Output file name without extension (default: from .env OUTPUT_FILENAME)"
    )
    args = parser.parse_args()

    input_file = args.input
    print(f"Reading text from: {input_file}")
    text = read_markdown(input_file)

    if not text:
        print("ERROR: No text found in the input file.")
        sys.exit(1)

    print("--- Text to synthesize ---")
    preview = text[:500] + ("..." if len(text) > 500 else "")
    print(preview)
    print("--------------------------\n")

    config = load_config()

    # Override output filename if provided via CLI
    if args.output:
        config["OUTPUT_FILENAME"] = args.output

    # Auto-detect whether this is a trial voice or a full personal voice
    print("Checking voice type...")
    if is_trial_voice(config):
        print("Detected: Trial personal voice\n")
        synthesize_trial(config, text)
    else:
        print("Detected: Full personal voice (using SDK)\n")
        synthesize_sdk(config, text)


if __name__ == "__main__":
    main()
