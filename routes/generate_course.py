from flask import Blueprint, request, jsonify
from groq import Groq
import os
from dotenv import load_dotenv

load_dotenv()

generate_course_route = Blueprint("generate_course", __name__)

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

@generate_course_route.route("/generate-course", methods=["POST"])
def generate_course():

    data = request.json
    topic = data.get("topic")

    prompt = f"""
Create a course for {topic}.

Return:

1. 5 learning modules
2. explanation for each module
3. 3 MCQ questions
4. 2 YouTube search topics
5. 2 article topics
"""

    completion = client.chat.completions.create(
        model="llama3-70b-8192",
        messages=[
            {"role": "user", "content": prompt}
        ]
    )

    result = completion.choices[0].message.content

    return jsonify({
        "topic": topic,
        "content": result
    })