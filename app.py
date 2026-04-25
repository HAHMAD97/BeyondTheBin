from ImageLLM import classify_current_item
from SpeechToText import listen_once

MAX_ARGUMENTS = 4  # threshold before AI gives up

from google import genai
import os

client = genai.Client(api_key=os.getenv("GEMMA_KEY"))


def respond_to_user(item_data, user_input):
    """
    Uses LLM to reply to user.
    """

    prompt = f"""
You are a grumpy AI smart trash can in Toronto (2026).

You already classified this item as:
- bin: {item_data.bin}
- explanation: {item_data.sass}

Now the user is arguing with you.

User says:
"{user_input}"

Rules:
- Be consistent with your original decision
- BUT you MUST explain your reasoning when asked (especially "why")
- If user asks "why is it toxic / wrong / e-waste", explain clearly
- Keep personality: grumpy, sarcastic, slightly annoyed
- Do NOT just repeat the same sentence
- Keep response under 4 sentences
"""

    response = client.models.generate_content(
        model="gemma-4-26b-a4b-it",
        contents=prompt,
    )

    return response.text


def run_trashcan_ai():
    print("Smart Trashcan Booting...\n")

    item = classify_current_item()

    if not item:
        print("Could not classify item.")
        return

    print("\nTRASHCAN SAYS:")
    print(item.sass)
    print(f"BIN: {item.bin.upper()}\n")

    # CASE 1: TRASH → END EARLY
    if item.bin.lower() == "trash":
        print("Trash detected, opening!")
        return

    # Otherwise: start argument loop
    argument_count = 0

    print("Listening for user response...\n")

    while argument_count < MAX_ARGUMENTS:
        user_text = listen_once()

        if not user_text:
            continue

        print(f"\nUSER: {user_text}")

        response = respond_to_user(item, user_text)

        print(f"TRASHCAN: {response}\n")

        # Simple escalation logic
        if any(word in user_text for word in ["stop", "fine", "ok", "whatever"]):
            print("TRASHCAN: Conversation terminated. Don't test me again.")
            break

        argument_count += 1

    if argument_count >= MAX_ARGUMENTS:
        print("TRASHCAN: I've repeated myself 4 times. I’m done arguing.")


if __name__ == "__main__":
    run_trashcan_ai()