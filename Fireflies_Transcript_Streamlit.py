import streamlit as st
import requests
from datetime import datetime

# Streamlit secrets for API key
API_KEY = st.secrets["FIREFLIES_API_KEY"]
BASE_URL = "https://api.fireflies.ai/graphql"

HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}


def to_iso8601(date_str):
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").isoformat() + "Z"
    except ValueError:
        st.error("Invalid date format. Please use YYYY-MM-DD.")
        return None


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
    if response.status_code == 200:
        data = response.json()
        return data.get("data", {}).get("transcripts", [])
    else:
        st.error(f"Error fetching transcripts: {response.text}")
        return []


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
    }
    """
    response = requests.post(BASE_URL, json={"query": query, "variables": {"transcriptId": transcript_id}},
                             headers=HEADERS)
    if response.status_code == 200:
        data = response.json()
        return data.get("data", {}).get("transcript", {})
    else:
        st.error(f"Error fetching transcript details: {response.text}")
        return {}


def consolidate_transcripts(transcripts):
    consolidated_text = ""
    for transcript in transcripts:
        details = fetch_transcript_details(transcript["id"])
        if details:
            title = details["title"]
            date = datetime.fromtimestamp(details["date"] / 1000).strftime("%Y-%m-%d")
            consolidated_text += f"Meeting Name: {title}\nMeeting Date: {date}\n\n"
            for sentence in details["sentences"]:
                speaker_name = sentence.get("speaker_id", "Unknown Speaker")
                raw_text = sentence.get("raw_text", "")
                consolidated_text += f"{speaker_name}: {raw_text}\n"
            consolidated_text += "\nEND MEETING\n\n"
    return consolidated_text


# Streamlit App
st.title("Fireflies Transcript Tool")

# Input fields
participant_email = st.text_input("Enter participant email:")
from_date = st.date_input("Start Date (optional):", value=None)
to_date = st.date_input("End Date (optional):", value=None)

if st.button("Fetch Transcripts"):
    if not participant_email:
        st.error("Participant email is required.")
    else:
        with st.spinner("Fetching transcripts..."):
            from_date_iso = to_iso8601(from_date.strftime("%Y-%m-%d")) if from_date else None
            to_date_iso = to_iso8601(to_date.strftime("%Y-%m-%d")) if to_date else None
            transcripts = fetch_transcripts(participant_email, from_date_iso, to_date_iso)

        if transcripts:
            st.success(f"Found {len(transcripts)} transcripts:")
            for idx, transcript in enumerate(transcripts, start=1):
                date = datetime.fromtimestamp(transcript["date"] / 1000).strftime("%Y-%m-%d")
                st.write(f"{idx}. {transcript['title']} - {date}")

            if st.button("Generate Consolidated File"):
                with st.spinner("Generating consolidated file..."):
                    consolidated_text = consolidate_transcripts(transcripts)

                st.download_button(
                    label="Download Consolidated File",
                    data=consolidated_text,
                    file_name="Consolidated_Transcripts.txt",
                    mime="text/plain"
                )
        else:
            st.warning("No transcripts found for the given filters.")