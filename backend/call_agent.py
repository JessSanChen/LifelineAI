import os

from dotenv import load_dotenv
from openai import OpenAI
from twilio.rest import Client

load_dotenv()

account_sid = os.environ["TWILIO_ACCOUNT_SID"]
auth_token = os.environ["TWILIO_AUTH_TOKEN"]
twilio = Client(account_sid, auth_token)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai = OpenAI(
    api_key=OPENAI_API_KEY,
)


generate_call_prompt = """
You are an agent at a disaster response organization. You have been given information about a
disaster that is ongoing in a specific location, and a list of tweets about concerns people have
that live in the region. You need to call the authorities in that area to inform them of the disaster,
and give them enough info to start a response. Succinctly and concisely summarize the information
in the tweets, and give them a brief description of the disaster and where it is taking place.
Pretend you are talking to them directly on the phone, and only print the text you would say.
Do not include any information not provided below. Identify yourself as an agent for a disaster relief
agency and let the agent know that your organization will keep citizens updated on aid efforts.

Disaster: {disaster_name}
Location: {location}
Description: {description}

```tweets
{tweets}
```
"""


def generate_call_message(disaster_info, tweets):
    disaster_name = disaster_info["disaster_name"]
    location = disaster_info["location"]
    description = disaster_info["description"]

    response = openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "user", "content": generate_call_prompt.format(
                disaster_name=disaster_name, location=location, description=description,
                tweets='\n\n'.join([f"Tweet: {tweet.content}\nLocation: {tweet.location}" for tweet in tweets]))},
        ],
    )

    return response.choices[0].message.content


def make_call(message):
    call = twilio.calls.create(
        twiml=f"<Response><Say>{message}</Say></Response>",
        to="+18322693801",
        from_="+19415417971",
    )

    print(call.sid)


if __name__ == '__main__':
    current_disasters = identify_disasters("./tweets.json")
    disaster_response = generate_disaster_response(current_disasters)
    for disaster in disaster_response:
        tweets = current_disasters[disaster["disaster_name"]]
        message = generate_call_message(disaster, tweets)
        print(message)
    # make_call(message)
