import os
import requests
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables
load_dotenv()

API_KEY = os.getenv("FIREFLIES_API_KEY")
BASE_URL = "https://api.fireflies.ai/graphql"

HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}

def to_iso8601(date_str):
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").isoformat() + "Z"
    except ValueError:
        raise ValueError(f"Invalid date format: {date_str}. Use YYYY-MM-DD.")

def format_date_for_filename(date_value):
    try:
        if isinstance(date_value, int):
            return datetime.fromtimestamp(date_value / 1000).strftime("%Y-%m-%d")
        elif isinstance(date_value, str):
            return datetime.fromisoformat(date_value[:-1]).strftime("%Y-%m-%d")
    except Exception as e:
        print(f"Error formatting date: {e}")
    return "unknown-date"

def fetch_transcripts(participant_email, from_date=None, to_date=None):
    query = """
    query ($participantEmail: String!, $fromDate: DateTime, $toDate: DateTime) {
        transcripts(participant_email: $participantEmail, fromDate: $fromDate, toDate: $toDate) {
            id
            title
            date
        }
    }
    """
    variables = {
        "participantEmail": participant_email,
        "fromDate": from_date,
        "toDate": to_date,
    }
    response = requests.post(BASE_URL, json={"query": query, "variables": variables}, headers=HEADERS)
    data = response.json()
    if response.status_code == 200 and "data" in data:
        return data["data"]["transcripts"]
    else:
        raise Exception(f"Error fetching transcripts: {data.get('errors')}")

def fetch_transcript_details(transcript_id):
    query = """
    query ($transcriptId: String!) {
        transcript(id: $transcriptId) {
            id
            title
            date
            sentences {
                raw_text
                speaker_id
            }
            speakers {
                id
                name
            }
        }
    """
    variables = {
        "transcriptId": transcript_id,
    }
    response = requests.post(BASE_URL, json={"query": query, "variables": variables}, headers=HEADERS)
    data = response.json()
    if response.status_code == 200 and "data" in data:
        return data["data"]["transcript"]
    else:
        raise Exception(f"Error fetching transcript details: {data.get('errors')}")

def save_transcripts_with_subfolder(transcripts, participant_email, output_dir):
    if not transcripts:
        print("No transcripts to save.")
        return None

    # Sort transcripts by date and get the date of the first transcript
    transcripts.sort(key=lambda t: t['date'])
    first_date = format_date_for_filename(transcripts[0]['date'])

    # Create a subfolder for the transcripts
    subfolder_name = f"{participant_email}_{first_date}_consolidated"
    subfolder_path = os.path.join(output_dir, subfolder_name)
    os.makedirs(subfolder_path, exist_ok=True)

    saved_files = []

    # Save each transcript in the subfolder
    for transcript in transcripts:
        meeting_title = transcript['title'].replace(' ', '_').replace('/', '_')
        meeting_date = format_date_for_filename(transcript['date'])
        file_name = f"{meeting_title}_{meeting_date}.txt"
        file_path = os.path.join(subfolder_path, file_name)

        # Fetch full transcript details
        details = fetch_transcript_details(transcript['id'])

        # Map speaker ID to speaker name
        speaker_mapping = {speaker['id']: speaker['name'] for speaker in details.get('speakers', [])}

        # Write transcript details to the file
        with open(file_path, "w", encoding="utf-8") as file:
            file.write(f"Meeting Name: {details['title']}\n")
            file.write(f"Meeting Date: {meeting_date}\n\n")
            for sentence in details['sentences']:
                speaker_id = sentence.get("speaker_id", "Unknown Speaker")
                speaker_name = speaker_mapping.get(speaker_id, "Unknown Speaker")
                raw_text = sentence.get("raw_text", "")
                file.write(f"{speaker_name}: {raw_text}\n")
            file.write("\nEND MEETING\n")

        saved_files.append(file_path)

    print(f"All transcripts saved in folder: {subfolder_path}")
    return subfolder_path, saved_files

def consolidate_transcripts(saved_files, output_dir, consolidated_filename="Consolidated_Transcripts.txt"):
    consolidated_path = os.path.join(output_dir, consolidated_filename)

    with open(consolidated_path, "w", encoding="utf-8") as consolidated_file:
        for file_path in saved_files:
            with open(file_path, "r", encoding="utf-8") as individual_file:
                consolidated_file.write(individual_file.read())
                consolidated_file.write("\n\n")  # Add two newlines between meetings

    print(f"Consolidated transcript saved at: {consolidated_path}")

def main():
    participant_email = input("Enter participant email: ").strip()
    from_date_input = input("Enter start date (YYYY-MM-DD, optional): ").strip()
    to_date_input = input("Enter end date (YYYY-MM-DD, optional): ").strip()

    if not participant_email:
        print("No participant email provided. Exiting.")
        return

    from_date = to_iso8601(from_date_input) if from_date_input else None
    to_date = to_iso8601(to_date_input) if to_date_input else None

    try:
        transcripts = fetch_transcripts(participant_email, from_date, to_date)
        if transcripts:
            print("The following transcripts were found:\n")
            for idx, transcript in enumerate(transcripts, start=1):
                meeting_date = format_date_for_filename(transcript['date'])
                print(f"{idx}. {transcript['title']} - {meeting_date}")

            confirm = input("\nDo you want to save these transcripts? (yes/no): ").strip().lower()
            if confirm in ("yes", "y"):
                subfolder_path, saved_files = save_transcripts_with_subfolder(transcripts, participant_email, "output")

                # Ask for consolidation
                consolidate_confirm = input("\nDo you want to create a consolidated transcript file? (yes/no): ").strip().lower()
                if consolidate_confirm in ("yes", "y"):
                    consolidate_transcripts(saved_files, subfolder_path)
            else:
                print("Transcript saving aborted.")
        else:
            print("No transcripts found for the given filters.")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()