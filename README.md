# VidSummary . Transforming Hours into Minutes, One Summary at a Time

Introducing VidSummary, an advanced video summarization tool that efficiently condenses lengthy videos while preserving the essence of the content. VidSummary leverages FFmpeg, whisperx ASR, and OpenAI's GPT-3.5-turbo to extract audio, transcribe speech, and generate concise summaries. The result? A streamlined output video showcasing only the most valuable segments, crafted with precision and accuracy preserving the original video for an optimal viewing experience.

## Prerequisites

1. You need to have Python 3.8 or newer installed.
2. Make sure you have FFmpeg installed and added to your system's PATH.
3. Set up OpenAI's Python library by running: `pip install openai`
4. Set up Whisperx's ASR tool (https://github.com/m-bain/whisperX)
5. Install the `python-dotenv` library by running: `pip install python-dotenv`
6. Install required Python libraries by running: `pip install -r requirements.txt`

## Configuration

1. Create a `.env` file in the project directory.
2. Add your OpenAI API key to the `.env` file as follows: OPENAI_KEY=your_openai_api_key_here

## Usage

To use the video summarization tool, run the following command:

```console
python vidsummary.py input_video_path output_video_path
```

Replace `input_video_path` with the path to the input video file and `output_video_path` with the desired path for the summarized output video.

## How It Works

1. The tool extracts audio from the input video using FFmpeg.
2. The extracted audio is transcribed to text using the whisperx ASR tool.
3. The transcriptions are divided into token groups to fit within GPT-3.5-turbo's token limit.
4. The token groups are sent to GPT-3.5-turbo for summarization.
5. The summarized text is used to create a filtered subtitle dictionary.
6. The input video is split into chunks based on the filtered subtitle dictionary.
7. The video chunks are concatenated to create the summarized output video.

Note: This project is designed to work with GPT-3.5-turbo, but it should also work with other OpenAI models by changing the `model` parameter in the `openai.ChatCompletion.create()` function.
