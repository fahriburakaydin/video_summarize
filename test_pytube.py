

from openai import OpenAI

# Set your OpenAI API key
client = OpenAI(api_key="REDACTED")


def summarize_text(text):
    """Summarizes text using OpenAI's GPT-4o-mini model."""
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "system", "content": 
                   """You are a helpful assistant that summarizes text. 
                   You will be given a transcript of a youtube video and you will need to summarize it in a few sentences.
                   Make sure to keep the most important information and remove any unnecessary details.
                   Use bullet points to list the important highlights
                   if it is multiple speakers, try to guess what is happening in the video, but don't make up anything.
                   Ensure that you make it clear when you are guessing what is happening in the video"""}, 
                  {"role": "user", "content": f"""Here is the transcript of the video you will summarize: {text}. 
                   Keep your summary concise and to the point. Make sure you clearly state what is covered in the video.
                   Use bullet points to list the important highlights"""}
                   ],
                   temperature=0.3,
        max_tokens=150
    )
    response_text = response.choices[0].message.content,
    tokens_used = response.usage.total_tokens
    return response_text, tokens_used

print(summarize_text("Hello, how are you?"))
