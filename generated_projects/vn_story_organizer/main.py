"""VN Story Organizer - Visual Novel storyline organization tool."""

import argparse
import sys
from pathlib import Path


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Organize and structure Visual Novel storylines."
    )
    parser.add_argument(
        "--input", "-i",
        type=str,
        default="",
        help="Path to VN script file or directory.",
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        default="output",
        help="Output directory for organized results.",
    )
    parser.add_argument(
        "--format",
        choices=["text", "json", "markdown"],
        default="markdown",
        help="Output format for the storyline summary.",
    )
    return parser.parse_args(argv)


def organize_storyline(input_path, output_dir, output_format):
    """Main storyline organization logic."""
    print(f"VN Story Organizer v0.1.0")
    print(f"Input:  {input_path or '(interactive mode)'}")
    print(f"Output: {output_dir}")
    print(f"Format: {output_format}")
    print()

    if not input_path:
        print("No input file specified. Running in interactive mode.")
        print("Use --input <path> to specify a VN script file.")
        print()
        print("Supported operations:")
        print("  1. Load VN script files")
        print("  2. Parse scenes and dialogues")
        print("  3. Organize by route/character")
        print("  4. Export structured summary")
        return 0

    path = Path(input_path)
    if not path.exists():
        print(f"Error: Input path does not exist: {input_path}", file=sys.stderr)
        return 1

    print(f"Loading scripts from: {path}")
    return 0


if __name__ == "__main__":
    args = parse_args()
    sys.exit(organize_storyline(args.input, args.output, args.format))
