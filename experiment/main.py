"""
Main entry point for the graph-based code review experiment
"""
import argparse
import sys
from pathlib import Path

from loguru import logger

from experiment.review_algorithm import ReviewAlgorithm
from experiment.graph_builder import GraphBuilder


def main():
    parser = argparse.ArgumentParser(
        description='Graph-based Code Review Experiment')
    parser.add_argument('file', help='Path to the code file to review')
    parser.add_argument('--language', default='python',
                        help='Programming language of the file')
    parser.add_argument(
        '--version', help='Language version (e.g., c90, c11, python3.8)')
    parser.add_argument('--graph-host', default='graphd',
                        help='Nebula graph host')
    parser.add_argument('--graph-port', type=int,
                        default=9669, help='Nebula graph port')
    parser.add_argument('--user', default='root', help='Nebula user')
    parser.add_argument('--password', default='password',
                        help='Nebula password')
    parser.add_argument('--space', default='code_graph',
                        help='Nebula space name')

    args = parser.parse_args()

    # Check if file exists
    file_path = Path(args.file)
    if not file_path.exists():
        logger.error(f"File does not exist: {file_path}")
        sys.exit(1)

    # Read the code from file
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            code = f.read()
    except Exception as e:
        logger.error(f"Error reading file: {e}")
        sys.exit(1)

    # Initialize the review algorithm
    review_algo = ReviewAlgorithm(
        args.graph_host, args.graph_port,
        args.user, args.password, args.space
    )

    # Perform the review
    # try:
    result = review_algo.review_code(
        code=code,
        file_path=str(file_path),
        language=args.language,
        version=args.version
    )

    # logger.info the results
    logger.info(f"\n=== Code Review Results for {file_path} ===")
    logger.info(f"Found {len(result.signals)} signals:")
    for signal in result.signals:
        logger.info(f"  - Line {signal.line_no}: [{signal.severity.upper()} {signal.signal_type.value}] {signal.message}")

    logger.info(f"\nFound {len(result.context)} related components:")
    # for ctx in result.context:
    #     logger.info(f"  - {ctx.get('type', 'Unknown')} {ctx.get('name', 'Unknown')} at line {ctx.get('line_start', 'Unknown')}")

    logger.info(f"\nFound {len(result.relationships)} relationships:")
    for rel in result.relationships:
        logger.info(f"  - Function {rel.get('name', 'Unknown')} in {rel.get('file_path', 'Unknown')} at line {rel.get('line_start', 'Unknown')}")

    # except Exception as e:
    #     logger.error(f"Error during code review: {e}")
    #     sys.exit(1)


if __name__ == '__main__':
    main()
