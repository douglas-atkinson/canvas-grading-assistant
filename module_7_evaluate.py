"""
Module 7: Evaluate one grading package with a configured model provider.

This script:
- loads a Module 6 grading package,
- loads AI-safe student material,
- performs a final privacy gate,
- builds one provider-neutral request,
- optionally writes a dry-run preview,
- sends exactly one request when --send is present,
- saves the raw and normalized structured response,
- validates the response against the supplied JSON Schema,
- makes no Canvas changes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from module_7.config import load_profile
from module_7.payload_loader import (
    load_json,
    load_response_schema,
    load_student_material,
)
from module_7.privacy import assert_ai_safe
from module_7.prompt_builder import (
    PROMPT_VERSION,
    build_model_request,
    find_first_anonymous_label,
    load_system_prompt,
)
from module_7.providers.factory import create_provider
from module_7.validation import validate_structured_response


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Send one anonymous grading package to a configured model "
            "provider and save one structured response."
        )
    )
    parser.add_argument(
        "grading_package",
        type=Path,
        help="Module 6 grading_package.json",
    )
    parser.add_argument(
        "student_material",
        type=Path,
        help=(
            "AI-safe student material JSON, text preview, or source directory"
        ),
    )
    parser.add_argument(
        "--response-schema",
        type=Path,
        help=(
            "Structured-output JSON Schema. May be omitted when embedded "
            "or referenced by the grading package."
        ),
    )
    parser.add_argument(
        "--profiles",
        type=Path,
        default=Path("config/model_profiles.json"),
        help="Model-profile JSON file",
    )
    parser.add_argument(
        "--profile",
        help="Named model profile; defaults to active_profile",
    )
    parser.add_argument(
        "--prompt",
        type=Path,
        default=Path("prompts/module_7_grading_prompt_v2.txt"),
        help="Version-controlled system prompt",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        help=(
            "Root output directory. Defaults beside the grading package "
            "under model_runs."
        ),
    )
    parser.add_argument(
        "--send",
        action="store_true",
        help=(
            "Actually call the configured provider. Without --send, "
            "Module 7 performs a dry run only."
        ),
    )
    parser.add_argument(
        "--skip-availability-check",
        action="store_true",
        help="Skip the provider/model metadata preflight",
    )
    return parser.parse_args()


def write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def safe_name(text: str) -> str:
    cleaned = "".join(
        character
        if character.isalnum() or character in {"-", "_"}
        else "_"
        for character in text
    )
    return cleaned.strip("_") or "unknown"


def create_run_directory(
    root: Path,
    provider_name: str,
    model_name: str,
) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_name = (
        f"{timestamp}_{safe_name(provider_name)}_"
        f"{safe_name(model_name)}"
    )
    run_directory = root / run_name
    run_directory.mkdir(parents=True, exist_ok=False)
    return run_directory


def main() -> int:
    args = parse_arguments()
    load_dotenv()

    try:
        grading_package_path = args.grading_package.resolve()
        grading_package = load_json(grading_package_path)
        student_material = load_student_material(
            args.student_material.resolve()
        )

        assert_ai_safe(student_material)

        response_schema = load_response_schema(
            grading_package=grading_package,
            grading_package_path=grading_package_path,
            schema_path=(
                args.response_schema.resolve()
                if args.response_schema
                else None
            ),
        )

        profile = load_profile(
            args.profiles.resolve(),
            args.profile,
        )
        system_prompt = load_system_prompt(args.prompt.resolve())

        model_request = build_model_request(
            grading_package=grading_package,
            student_material=student_material,
            response_schema=response_schema,
            system_prompt=system_prompt,
            response_format_name=profile.response_format_name,
        )

        total_input_characters = (
            len(model_request.system_prompt)
            + len(model_request.user_prompt)
        )
        if total_input_characters > profile.max_input_characters:
            raise ValueError(
                "Model request exceeds configured max_input_characters: "
                f"{total_input_characters:,} > "
                f"{profile.max_input_characters:,}"
            )

        output_root = (
            args.output_dir.resolve()
            if args.output_dir
            else grading_package_path.parent / "model_runs"
        )
        output_root.mkdir(parents=True, exist_ok=True)

        mode_name = "send" if args.send else "dry_run"
        run_directory = create_run_directory(
            output_root,
            profile.provider,
            profile.model,
        )

        request_payload = {
            "module": "7",
            "mode": mode_name,
            "provider_profile": {
                "profile_name": profile.profile_name,
                "provider": profile.provider,
                "model": profile.model,
                "reasoning_effort": profile.reasoning_effort,
                "max_output_tokens": profile.max_output_tokens,
                "store": False,
            },
            "prompt_version": PROMPT_VERSION,
            "system_prompt": model_request.system_prompt,
            "user_prompt": model_request.user_prompt,
            "response_schema": model_request.response_schema,
            "metadata": model_request.metadata,
        }
        write_json(
            run_directory / "request_payload.json",
            request_payload,
        )

        request_manifest = {
            "module": "7",
            "mode": mode_name,
            "grading_package_path": str(grading_package_path),
            "student_material_path": str(
                args.student_material.resolve()
            ),
            "profiles_path": str(args.profiles.resolve()),
            "prompt_path": str(args.prompt.resolve()),
            "anonymous_label": (
                find_first_anonymous_label(student_material)
                or find_first_anonymous_label(grading_package)
            ),
            "input_character_count": total_input_characters,
            "system_prompt_sha256": sha256_text(
                model_request.system_prompt
            ),
            "user_prompt_sha256": sha256_text(
                model_request.user_prompt
            ),
            "response_schema_sha256": sha256_text(
                json.dumps(
                    model_request.response_schema,
                    sort_keys=True,
                    separators=(",", ":"),
                )
            ),
            "canvas_contacted": False,
            "provider_contacted": args.send,
        }
        write_json(
            run_directory / "request_manifest.json",
            request_manifest,
        )

        print("=" * 78)
        print("MODULE 7 REQUEST")
        print("=" * 78)
        print(f"Mode:             {mode_name}")
        print(f"Provider profile: {profile.profile_name}")
        print(f"Provider:         {profile.provider}")
        print(f"Model:            {profile.model}")
        print(f"Input characters: {total_input_characters:,}")
        print(f"Run directory:    {run_directory}")
        print("Canvas contacted: No")

        if not args.send:
            print("\nDRY RUN COMPLETE")
            print("No model provider was contacted.")
            print(
                "Review request_payload.json, then rerun with --send."
            )
            return 0

        provider = create_provider(profile)

        if not args.skip_availability_check:
            print("\nChecking provider and model availability...")
            provider.check_availability()

        print("Sending exactly one grading request...")
        provider_response = provider.evaluate(model_request)

        write_json(
            run_directory / "raw_provider_response.json",
            provider_response.raw_response,
        )

        expected_label = (
            find_first_anonymous_label(student_material)
            or find_first_anonymous_label(grading_package)
        )
        grading_result, validation_report = (
            validate_structured_response(
                output_text=provider_response.output_text,
                response_schema=response_schema,
                expected_anonymous_label=expected_label,
                grading_package=grading_package,
                student_material=student_material,
            )
        )

        if grading_result is not None:
            write_json(
                run_directory / "grading_result.json",
                grading_result,
            )

        write_json(
            run_directory / "validation_report.json",
            validation_report,
        )

        run_metadata = {
            "module": "7",
            "provider": provider_response.provider_name,
            "model": provider_response.model_name,
            "profile": profile.profile_name,
            "status": provider_response.status,
            "response_id": provider_response.response_id,
            "elapsed_seconds": provider_response.elapsed_seconds,
            "usage": provider_response.usage,
            "schema_enforced_by_provider": (
                provider_response.schema_enforced
            ),
            "finish_reason": provider_response.finish_reason,
            "incomplete_details": (
                provider_response.incomplete_details
            ),
            "structured_response_valid": (
                validation_report.get("valid", False)
            ),
            "store": False,
            "canvas_contacted": False,
        }
        write_json(
            run_directory / "run_metadata.json",
            run_metadata,
        )

        print("\nMODEL RESPONSE SAVED")
        print(f"Provider status: {provider_response.status}")
        print(
            "Structured result valid: "
            f"{validation_report.get('valid', False)}"
        )
        print(
            f"Elapsed seconds: {provider_response.elapsed_seconds:.2f}"
        )
        print(f"Run directory: {run_directory}")
        print("Canvas contacted: No")

        if not validation_report.get("valid", False):
            print("\nRESULT: REVIEW REQUIRED")
            return 2

        print("\nRESULT: STRUCTURED GRADING SUGGESTION SAVED")
        return 0

    except Exception as error:
        print("\nMODULE 7 FAILED")
        print(error)
        print("\nNo Canvas changes were made.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
