from docx.oxml.ns import qn


def preserve_run_spaces(run) -> None:
    """Tell Word to keep leading, trailing, and multiple spaces in a run."""
    for t_elem in run._element.findall(qn('w:t')):
        t_elem.set(qn('xml:space'), 'preserve')


def add_run_preserved(paragraph, text: str):
    """Add a run with whitespace preserved."""
    run = paragraph.add_run(text)
    preserve_run_spaces(run)
    return run
