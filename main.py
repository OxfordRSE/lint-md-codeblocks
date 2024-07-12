import os
import re
import subprocess
import sys
import argparse


def get_markdown_files(directory):
    """
    Get all .md files in the specified directory that do not have "slides" in their name.

    Args:
    - directory (str): The directory to search for .md files.

    Returns:
    - list: A list of matching .md file paths.
    """
    markdown_files = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.md') and 'slides' not in root:
                markdown_files.append(os.path.join(root, file))
    return markdown_files


def find_code_blocks(content):
    """
    Find all markdown code blocks and non-code text in the given content.

    Args:
    - content (str): The content to search for code blocks.

    Returns:
    - list: A list of tuples where each tuple contains a boolean indicating if the block is code and the block content.
    """
    code_block_pattern = re.compile(
        r"(?:```|~~~)(python)?\s*\n(.*?)\n(?:```|~~~)",
        re.DOTALL
    )

    parts = []
    last_pos = 0

    for match in code_block_pattern.finditer(content):
        if match.start() > last_pos:
            parts.append((False, content[last_pos:match.start()]))
        parts.append((bool(match.group(1)), match.group(2)))
        last_pos = match.end()

    if last_pos < len(content):
        parts.append((False, content[last_pos:]))

    return parts


def main(directory="."):
    files = get_markdown_files(directory)
    found_errors = False
    for file in files:
        with open(file, 'r') as f:
            relative_path = os.path.relpath(file, directory)
            fname = os.path.basename(file).replace('.md', '.py')
            content = f.read()
            parts = find_code_blocks(content)
            if not any(is_code for is_code, _ in parts):
                # Skip the file if there are no Python code blocks
                continue
            py_content = join_code_blocks(parts)
            if not py_content:
                continue
            with open(fname, 'w') as out:
                out.write(py_content)

            result = subprocess.run(['flake8', fname], capture_output=True, text=True)

            output = result.stdout.strip()
            if output:
                found_errors = True
                for line in output.split('\n'):
                    print(line.replace(fname, f'{relative_path}'))
            os.remove(fname)
    return 1 if found_errors else 0


def join_code_blocks(parts):
    """
    Join all code block contents together into one string, with non-code blocks as comments.

    Args:
    - parts (list): A list of tuples, where each tuple contains a boolean indicating if the block is code and the block content.

    Returns:
    - str: A single string containing all joined code block contents with non-code parts as comments.
    """
    all_blocks = []

    for is_code, block in parts:
        if is_code:
            all_blocks.append(block)
        else:
            comment_block = "\n".join("# " + line for line in block.split("\n"))
            all_blocks.append(comment_block)

    return "\n".join(all_blocks)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Lint Python code blocks in Markdown files.')
    parser.add_argument('directory', nargs='?', default=os.getcwd(), help='The base directory to scan for Markdown files (default: current directory).')
    args = parser.parse_args()

    print(args.directory)
    exit_code = main(args.directory)
    sys.exit(exit_code)