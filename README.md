# Personal Voice Text-to-Speech

Python script that reads text from a Markdown file and generates audio using [Azure Personal Voice](https://learn.microsoft.com/azure/ai-services/speech-service/personal-voice-overview) TTS.

## Features

- Reads text from any Markdown file (strips formatting automatically)
- Multiple speech styles: **Cheerful**, **Excited**, **Enthusiastic**, **Friendly**, and **Prompt** (neutral)
- Multi-language support (en-US, es-ES, de-DE, fr-FR, ja-JP, etc.)
- Output as WAV or MP3
- Auto-detects trial vs full personal voices
- Configurable via `.env` file or CLI arguments

## Prerequisites

1. An **Azure Speech Service** resource in a [supported region](https://learn.microsoft.com/azure/ai-services/speech-service/regions#personal-voice) (e.g. `eastus`, `westeurope`, `southeastasia`)
2. A **Personal Voice** created either:
   - Via [Speech Studio](https://speech.microsoft.com/portal/personalvoice) (trial voice)
   - Via the [Custom Voice REST API](https://learn.microsoft.com/azure/ai-services/speech-service/personal-voice-create-voice) (full voice)
3. **Python 3.8+**

## Setup

### 1. Clone the repository

```bash
git clone https://github.com/isabelcabezasm/tts-personal-voice.git
cd tts-personal-voice
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure

Copy the template and fill in your values:

```bash
cp temp.env .env
```

Edit `.env` with your Azure credentials:

```text
SPEECH_KEY=your_speech_subscription_key
SPEECH_REGION=eastus
SPEAKER_PROFILE_ID=your_speaker_profile_id
SPEECH_LANGUAGE=en-US
SPEECH_STYLE=Cheerful
OUTPUT_FORMAT=mp3
OUTPUT_FILENAME=output
```

> See `temp.env` for detailed comments on each setting.

## Usage

### Basic

Write your text in `input.md`, then run:

```bash
python synthesize.py
```

### Custom input file

```bash
python synthesize.py my_script.md
```

### Custom output name

```bash
python synthesize.py -o my_recording
```

### Both

```bash
python synthesize.py presentation.md -o demo
```

## Speech Styles

Set `SPEECH_STYLE` in your `.env` file to control the tone:

| Style           | Description                        | Prosody Boost        |
|-----------------|------------------------------------|----------------------|
| `Cheerful`      | Upbeat and positive                | +8% rate, +5% pitch  |
| `Excited`       | High energy, enthusiastic          | +12% rate, +8% pitch |
| `Enthusiastic`  | Eager and engaged                  | +10% rate, +6% pitch |
| `Friendly`      | Warm and approachable              | +5% rate, +3% pitch  |
| `Prompt`        | Neutral (no adjustments)           | None                 |

## Project Structure

```
├── synthesize.py      # Main script
├── input.md           # Your text to synthesize
├── temp.env           # Configuration template
├── requirements.txt   # Python dependencies
├── .gitignore         # Excludes .env and audio files
└── .env               # Your config (not tracked by git)
```

## How It Works

1. Reads a Markdown file and strips formatting (headings, bold, links, code blocks, etc.)
2. Auto-detects whether your Speaker Profile ID belongs to a **trial** or **full** personal voice
3. Builds SSML with the `DragonLatestNeural` voice, your speaker profile, style, and prosody settings
4. Synthesizes audio via the [Azure Speech SDK](https://pypi.org/project/azure-cognitiveservices-speech/) (full voices) or the trial REST API (trial voices)
5. Saves the result as a WAV or MP3 file

## Finding Your Speaker Profile ID

### For full voices (created via REST API)

The `speakerProfileId` is returned when you create the personal voice. You can also query it:

```bash
curl -X GET \
  "https://<region>.api.cognitive.microsoft.com/customvoice/personalvoices/?api-version=2024-02-01-preview" \
  -H "Ocp-Apim-Subscription-Key: <your_key>"
```

### For trial voices (created via Speech Studio)

1. Open [Speech Studio](https://speech.microsoft.com/portal/personalvoice) > Personal Voice
2. Open browser Dev Tools (F12) > Network tab
3. Reload the page
4. Look for requests to `/customvoice/trial/zeroshots/` and copy the GUID from the URL

> **Note:** Trial voices can only synthesize predefined scripts, not custom text. For custom text synthesis, create a full personal voice via the REST API.

## License

MIT
