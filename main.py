from __future__ import annotations

from pathlib import Path

from agent.intent_detector import IntentDetector
from agent.llm_engine import LlmEngine
from agent.tool_router import RouterState, gmail_get_full, gmail_list_latest, gmail_send_reply
from config.gmail_config import GmailConfig
from config.model_config import ModelConfig
from tools.gmail_auth import get_gmail_service, sign_out
from utils.logger import Logger, log_event


def _print_help() -> None:
    print(
        "\nCommands (say or type):\n"
        "- 'read latest emails'\n"
        "- 'fetch the last 2 mails'\n"
        "- 'show last 10 emails'\n"
        "- 'reply 2' (after reading latest)\n"
        "- 'sign out'\n"
        "- 'help'\n"
        "- 'quit'\n"
    )


def main() -> None:
    logger = Logger().build()
    gmail_cfg = GmailConfig()
    model_cfg = ModelConfig()

    try:
        service = get_gmail_service(gmail_cfg)
        log_event(logger, "gmail_auth_ready", scopes=list(gmail_cfg.scopes))
    except FileNotFoundError as e:
        print(str(e))
        print("Fix: put your Desktop OAuth client JSON at 'secrets/oauth_client.json' (see README).")
        return
    except Exception as e:
        print(f"Failed to initialize Gmail auth: {e}")
        return

    # Voice is optional (depends on extra deps). If unavailable, app runs in text mode.
    stt = None
    ptt = None
    try:
        from voice.push_to_talk import AudioCaptureConfig, PushToTalk
        from voice.stt import SpeechToText

        stt = SpeechToText(model=model_cfg.whisper_model)
        ptt = PushToTalk(AudioCaptureConfig())
    except Exception as e:
        log_event(logger, "voice_disabled", reason=str(e))

    llm = LlmEngine(
        model_dir=str(model_cfg.qwen_model_dir),
        temperature=model_cfg.temperature,
        max_new_tokens=model_cfg.max_new_tokens,
        max_input_chars=model_cfg.max_input_chars,
    )
    intent_detector = IntentDetector(llm=llm)

    state = RouterState(latest=[])

    print("Local Gmail Voice Agent (V1)")
    _print_help()
    if ptt is not None and stt is not None:
        print("Tip: hold SPACE to record voice; press Enter to use text instead.\n")
    else:
        print("Voice mode unavailable (missing optional deps). Using text-only mode.")
        print("Fix: python -m pip install -r requirements-voice.txt\n")

    while True:
        # Try voice capture; if it fails, fallback to text input.
        wav_path = Path("runtime") / "last_command.wav"
        transcript = ""
        if ptt is not None and stt is not None:
            try:
                got_audio = ptt.record_while_held(wav_path)
                if got_audio:
                    stt_res = stt.transcribe_wav(str(wav_path))
                    transcript = stt_res.text.strip()
            except Exception as e:
                log_event(logger, "voice_capture_error", error=str(e))

        if not transcript:
            transcript = input("You> ").strip()

        if not transcript:
            continue
        if transcript.lower() in {"q", "quit", "exit"}:
            break

        intent = intent_detector.detect(transcript)
        log_event(
            logger,
            "intent",
            text=transcript,
            intent=intent.name,
            index=intent.message_index,
            max_results=intent.max_results,
        )

        if intent.name == "help":
            _print_help()
            continue

        if intent.name == "sign_out":
            ok = sign_out(gmail_cfg)
            print("Signed out (token deleted)." if ok else "No token found to delete.")
            continue

        if intent.name == "read_latest":
            try:
                max_results = intent.max_results or gmail_cfg.list_max_results
                state.latest = gmail_list_latest(service, max_results, gmail_cfg.list_query)
                if not state.latest:
                    print("No messages found.")
                    continue
                print("\nLatest emails:")
                for i, m in enumerate(state.latest, start=1):
                    print(f"{i}. {m.from_} | {m.subject} | {m.snippet}")
                print()
            except Exception as e:
                print(f"Error reading Gmail: {e}")
            continue

        if intent.name == "reply_draft":
            if not intent.message_index or intent.message_index < 1:
                print("Say 'reply 2' (choose a number from the latest list).")
                continue
            if not state.latest:
                print("First say 'read latest emails' so I can show you numbered emails.")
                continue
            if intent.message_index > len(state.latest):
                print(f"Invalid email number. Choose 1-{len(state.latest)}.")
                continue

            chosen = state.latest[intent.message_index - 1]
            try:
                full = gmail_get_full(service, chosen.id)
                state.selected = full
            except Exception as e:
                print(f"Error fetching email: {e}")
                continue

            draft = llm.draft_reply(
                email_from=state.selected.from_,
                subject=state.selected.subject,
                email_body=state.selected.body_text,
            )
            state.draft = draft.text
            print("\n--- DRAFT REPLY (not sent) ---")
            if draft.used_model:
                print("[Info] Drafted with local Qwen model.\n")
            else:
                print("[Info] Fallback template used (model not loaded).\n")
            print(state.draft)
            print("--- END DRAFT ---\n")

            confirm = input("Send this reply now? (y/N): ").strip().lower()
            if confirm not in {"y", "yes"}:
                print("Not sent.")
                continue

            try:
                assert state.selected is not None and state.draft is not None
                res = gmail_send_reply(service, state.selected, state.draft)
                print(f"Sent. Gmail message id: {res.id}")
                log_event(logger, "sent", message_id=res.id, thread_id=res.thread_id)
            except Exception as e:
                print(f"Error sending: {e}")
            continue

        print("Sorry, I didn't understand. Say 'help' for examples.")


if __name__ == "__main__":
    main()

