
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
    Find all markdown code blocks in the given content.

    Args:
    - content (str): The content to search for code blocks.

    Returns:
    - list: A list of code block contents.
    """
    code_block_pattern = re.compile(
        r"(?:```|~~~)\s*python\s*\n(.*?)\n(?:```|~~~)", 
        re.DOTALL
    )
    return code_block_pattern.findall(content)

def main(directory="."):
    files = get_markdown_files(directory)
    found_errors = False
    for file in files:
        with open(file, 'r') as f:
            fname = os.path.basename(file).replace('.md', '.py')
            content = f.read()
            code_blocks = find_code_blocks(content)
            py_content = join_code_blocks(code_blocks)
            if not py_content:
                continue
            with open(fname, 'w') as out:
                out.write(py_content)

            result = subprocess.run(['flake8', fname], capture_output=True, text=True)

            output = result.stdout.strip()
            if output:
                found_errors = True
                for line in output.split('\n'):
                    print(line.replace('.py:', f'.md:'))
            os.remove(fname)
    return found_errors
            
def join_code_blocks(code_blocks):
    """
    Join all code block contents together into one string.

    Args:
    - contents (list): A list of strings, each representing the content of a file.

    Returns:
    - str: A single string containing all joined code block contents.
    """
    all_code_blocks = []
    
    for block in code_blocks:
        all_code_blocks.append(block)  # Append only the code content

    return "\n".join(all_code_blocks)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Lint Python code blocks in Markdown files.')
    parser.add_argument('directory', nargs='?', default=os.getcwd(), help='The base directory to scan for Markdown files (default: current directory).')
    args = parser.parse_args()

    print(args.directory)
    sys.exit(main(args.directory))