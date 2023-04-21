import re
import sys
import tiktoken
import openai
import os
import subprocess
import shutil
from pathlib import Path
from dotenv import load_dotenv
import sentence_similarity
from collections import OrderedDict

DOTENV_PATH = Path(".") / ".env"
load_dotenv(dotenv_path=DOTENV_PATH)
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

def read_srt(file_path):
    """
    This function returns a dictionary with the subtitles as key and their timestamps as value
    """
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            content = file.read()
            blocks = re.split(r'\n\n', content)
            subtitles = OrderedDict()

            for block in blocks:
                if block.strip() == "":
                    continue

                lines = block.split('\n')
                if len(lines) >= 3:
                    # Extract timestamp
                    timestamp = lines[1].strip()

                    # Combine subtitle lines
                    subtitle = " ".join(lines[2:]).strip()

                    # Add subtitle and timestamp to ordered dictionary
                    subtitles[subtitle] = timestamp
    except:
        print("Error reading SRT file")
        return None
        
    return subtitles

def generate_srt(video_path, output_dir='temp'):
    # Create output directory if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Extract audio from the input video
    audio_path = os.path.join(output_dir, 'temp_audio.wav')
    extract_audio_command = f'ffmpeg -y -i "{video_path}" -vn -acodec pcm_s16le -ar 16000 -ac 1 "{audio_path}"'
    subprocess.run(extract_audio_command, shell=True, check=True)

    # Generate SRT using whisperx
    srt_path = os.path.join(output_dir, 'temp_audio.srt')
    whisperx_command = f'whisperx --model small --output_dir "{output_dir}" --output_format srt "{audio_path}"'
    subprocess.run(whisperx_command, shell=True, check=True)

    return srt_path

def count_tokens(text):
    """Count the number of tokens in a given text with tiktoken"""
    tokenizer = tiktoken.get_encoding("cl100k_base")
    tokenized_text = tokenizer.encode(text)

    return len(tokenized_text)

def build_subtitle_groups(subtitles_dict, max_tokens=1700):
    groups = []
    current_group = []
    current_token_count = 0

    for subtitle, timestamp in subtitles_dict.items():
        subtitle_with_newline = subtitle + "\n"
        subtitle_token_count = count_tokens(subtitle_with_newline)

        if current_token_count + subtitle_token_count <= max_tokens:
            current_group.append(subtitle_with_newline)
            current_token_count += subtitle_token_count
        else:
            groups.append(current_group)
            current_group = [subtitle_with_newline]
            current_token_count = subtitle_token_count

    if current_group:
        groups.append(current_group)

    print(f"Split subtitles into {len(groups)} groups")
    print(groups)
    return groups

def create_filtered_dict(summaries, subtitles_dict):
    print("Creating filtered dictionary...")
    filtered_dict = OrderedDict()
    last_sub_index = 0

    for summary in summaries:
        list_of_subtitles = summary.split("\n")
        for subtitle in list_of_subtitles:
            if subtitle in subtitles_dict.keys():
                filtered_dict[subtitle] = subtitles_dict[subtitle]
                last_sub_index = list(subtitles_dict.keys()).index(subtitle)
            else:
                #Check if the subtitle is similar to any of next 3 subtitles indexes in the subtitles_dict
                similar_sub = False
                for i in range(0, 3):
                    if last_sub_index + i < len(subtitles_dict):
                        if sentence_similarity.similar_sentences(subtitle, list(subtitles_dict.keys())[last_sub_index + i]):
                            filtered_dict[list(subtitles_dict.keys())[last_sub_index + i]] = subtitles_dict[list(subtitles_dict.keys())[last_sub_index + i]]
                            similar_sub = True
                            last_sub_index = last_sub_index + i
                            print(f"Similar subtitle found for {subtitle}")
                            break
                if not similar_sub:
                    print(f"Subtitle not found for {subtitle}")

                
    return filtered_dict

def get_subtitle_summary(subtitles_str, group_number=1):
    """
    This function returns the summarized subtitles using ChatGPT
    """
    print(f"Getting summary from ChatGPT for the subtitles group {group_number}...")
    raw_subtitles = repr(subtitles_str)
    prompt = f"Return the exact same text, but remove the sentences that are not important (sentences are separated by new lines '\\n') to the message in order to shorten the text. Keep full sentences intact with punctuation. Separate output with new lines:\n{raw_subtitles}"
    completion = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            # {"role": "system", "content": "You are an helpfull AI assistant"},
            {"role": "user", "content": prompt},
        ]
    )
    return completion.choices[0]['message']['content']

def summarize_subtitles(subtitles_dict, max_tokens=2000):
    """
    This function returns a dictionary with the subtitles and their timestamps
    """
    # Split subtitles into groups of 2000 tokens or less
    subtitle_groups = build_subtitle_groups(subtitles_dict, max_tokens)

    # Get summary for each group
    summaries = []
    group_number = 1
    for group in subtitle_groups:
        group_str = "".join(group)
        summary = get_subtitle_summary(group_str, group_number)
        summaries.append(summary)
        group_number += 1

    # Create a dictionary with the filtered subtitles
    print(summaries)
    filtered_dict = create_filtered_dict(summaries, subtitles_dict)
    print(filtered_dict)

    return filtered_dict

def split_video(input_video, filtered_subtitles_dict, output_video, temp_folder="temp"):
    # Create a temporary folder for storing video chunks
    os.makedirs(temp_folder, exist_ok=True)

    # Split video into chunks using the timestamps from the filtered dictionary
    chunks = []
    timestamps = list(filtered_subtitles_dict.values())

    for i, timestamp in enumerate(timestamps):
        start_time = timestamp.split(" --> ")[0].replace(",", ".")
        end_time = timestamp.split(" --> ")[1].replace(",", ".")
        chunk_name = f"{temp_folder}/chunk_{i:04d}.mp4"
        chunks.append(chunk_name)

        # Split the video using FFmpeg
        split_command = f'ffmpeg -v quiet -stats -y -i "{input_video}" -ss {start_time} -to {end_time} -c:v libx264 -crf 23 -preset medium -c:a aac -b:a 128k -reset_timestamps 1 "{chunk_name}"'
        subprocess.run(split_command, shell=True, check=True)

    # Create a text file containing the paths to the video chunks
    concat_list_path = f"{temp_folder}/concat_list.txt"
    with open(concat_list_path, "w") as concat_list_file:
        concat_list_file.writelines(f"file '{os.path.basename(chunk)}'\n" for chunk in chunks)

    # Join the chunks into a single video using the FFmpeg concat demuxer
    # join_command = f'ffmpeg -y -f concat -safe 0 -i "{concat_list_path}" -c copy "{output_video}"'
    join_command = f'ffmpeg -y -f concat -safe 0 -i "{concat_list_path}" -c copy "{output_video}"'
    subprocess.run(join_command, shell=True, check=True)

    # Clean up the temporary folder
    shutil.rmtree(temp_folder)

def main():
    # Get the input video path
    input_video = sys.argv[1]

    # Get the output video path
    output_video = sys.argv[2]

    # Generate SRT file
    if read_srt(os.path.join('temp', 'temp_audio.srt')):
        srt_path = os.path.join('temp', 'temp_audio.srt')
    else:
        srt_path = generate_srt(input_video)

    # Load SRT file
    subtitles_dict = read_srt(srt_path)

    # Summarize subtitles
    openai.api_key = OPENAI_API_KEY
    filtered_subtitles_dict = summarize_subtitles(subtitles_dict)

    # Split video
    split_video(input_video, filtered_subtitles_dict, output_video)

if __name__ == "__main__":
    main()
