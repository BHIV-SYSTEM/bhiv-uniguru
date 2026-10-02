import argparse
import json

from .runtime import DecoderRuntime


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the UniGuru Sanskrit decoder")
    parser.add_argument("concept", nargs="?", default="धर्म", help="Sanskrit concept to decode")
    args = parser.parse_args()

    runtime = DecoderRuntime()
    result = runtime.execute(args.concept)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
