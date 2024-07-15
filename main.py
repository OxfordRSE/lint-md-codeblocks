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
    print(os.listdir(directory))
    markdown_files = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.md') and 'slides' not in root:
                markdown_files.append(os.path.join(root, file))
    return markdown_files


def find_code_blocks(content):
    code_block_pattern = re.compile(
        r"^(\s*)(```|~~~)(.*?)\s*\n(.*?)(^\s*\2\s*$)", re.DOTALL | re.MULTILINE
    )
    parts = []
    last_pos = 0

    for match in code_block_pattern.finditer(content):
        if match.start() > last_pos:
            non_code_content = content[last_pos:match.start()]
            comment_block = "\n".join("# " + line for line in non_code_content.split("\n"))
            parts.append((False, comment_block))

        leading_spaces = match.group(1)[1:]
        lang_line = match.group(3).strip()
        code = match.group(4)
        end_block = match.group(5)

        if lang_line.startswith('python') and 'nolint' not in lang_line:
            stripped_lines = []
            for line in code.split('\n'):
                if line.startswith(' ' * len(leading_spaces)):
                    stripped_lines.append(line[len(leading_spaces):])
                else:
                    stripped_lines.append(line)
            parts.append((True, ('\n').join(stripped_lines)))
        else:
            parts.append((False, match.group(0)))

        last_pos = match.end()

    if last_pos < len(content):
        non_code_content = content[last_pos:]
        comment_block = "\n".join("# " + line for line in non_code_content.split("\n"))
        parts.append((False, comment_block))
    return parts



def main(directory, flake8_config):
    files = get_markdown_files(directory)
    found_errors = False
    for file in files:
        with open(file, 'r') as f:
            relative_path = os.path.relpath(file, directory)
            fname = os.path.basename(file).replace('.md', '.py')
            content = f.read()
            parts = find_code_blocks(content)
            if not any(is_code for is_code, _ in parts):
                continue
            py_content = join_code_blocks(parts)
            if not py_content:
                continue
            with open(".tmp/" + fname, 'w') as out:
                out.write(py_content)
            result = subprocess.run(['flake8', f'--config={flake8_config}', ".tmp/" + fname], capture_output=True, text=True)
            output = result.stdout.strip()
            if output:
                found_errors = True
                lines = py_content.splitlines()
                for line in output.split('\n'):
                    error_line_num = int(line.split(':')[1]) - 1
                    error_line = lines[error_line_num]
                    print(f"{line.replace(fname, relative_path)}\n    {error_line}")
            os.remove(".tmp/" + fname)
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
    parser.add_argument('flake8_config', help='Path to the flake8 configuration file')
    args = parser.parse_args()
    print(f"Scanning directory: {args.directory}")
    print(f"Using flake8 config: {args.flake8_config}")
    exit_code = main(args.directory, args.flake8_config)
    print(f"Exit code: {exit_code}")
    sys.exit(exit_code)