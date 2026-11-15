"""Tests for finding a task's subject."""

import pytest

from custom_components.firefly_cloud.subjects import class_subjects, normalise, title_subject, with_subjects

TIMETABLE = {"pabc1 b": "Year 8 Performing Arts", "ds8 b": "Year 8 Discovery", "msbs2 b": "Year 8 Science"}


def _week_event(code, subject):
    return {"subject": subject, "description": f"{code}\nAttendees: Unknown, Unknown"}


def test_normalise():
    """Codes and names compare ignoring case and spacing."""
    assert normalise("  PABC1   B ") == "pabc1 b"


def test_class_subjects_from_lesson_descriptions():
    """Each class code (first line of a lesson's description) maps to its lesson's subject, normalised."""
    events = [
        _week_event("PABC1 B", "Year 8 Performing Arts"),
        _week_event("PABC1  b", "Something else"),
        {"subject": "No description"},
        {"description": "NOSUBJ A"},
    ]
    assert class_subjects(events) == {"pabc1 b": "Year 8 Performing Arts"}


def test_subject_found_from_class_in_timetable():
    """Tasks have no subject; the class they were set for is matched to the timetable's subject."""
    tasks = [
        {"id": 1, "title": "A", "addressees": [{"name": "Class PABC1 B", "isGroup": True}]},
        {"id": 2, "title": "B", "addressees": [{"name": "Class DS8 E"}, {"name": "class  ds8 b"}]},
        {"id": 3, "title": "C", "addressees": [{"name": "A Student", "isGroup": False}]},
        {"id": 4, "title": "D", "subject": {"name": "History"}, "addressees": [{"name": "Class PABC1 B"}]},
        {"id": 5, "title": "E"},
        {"id": 6, "title": "F", "subject": "", "addressees": [{"name": "Class PABC1 B"}]},
        {"id": 7, "title": "G", "subject": None, "addressees": [{"name": "Class PABC1 B"}]},
    ]
    result = with_subjects(tasks, TIMETABLE)
    assert [t.get("subject") for t in result] == [
        "Year 8 Performing Arts",
        "Year 8 Discovery",
        None,
        {"name": "History"},
        None,
        "Year 8 Performing Arts",
        "Year 8 Performing Arts",
    ]
    assert "subject" not in tasks[0]  # the raw fetch is left as it was


@pytest.mark.parametrize(
    ("title", "subject"),
    [
        ("Discovery: Passion Project (Psych Lab)", "Year 8 Discovery"),
        ("8 Discovery: Project Round 2", "Year 8 Discovery"),
        ("Year 8 Science: Forces", "Year 8 Science"),
        ("discovery : lowercase and spaced", "Year 8 Discovery"),
        ("Year 8 Discovery: full name", "Year 8 Discovery"),
        # Not subjects on the timetable
        ("Homework: read ch 3", None),
        ("Reminder: bring kit", None),
        ("Week 3: vocab", None),
        ("Task 1: Essay", None),
        ("Hand in by 3:30pm", None),
        ("See https://example.com/x", None),
        ("Year 8: Maths quiz", None),
        ("Music Technology: Composition", None),
        ("Read chapter 3", None),
        (": no prefix", None),
        (None, None),
    ],
)
def test_title_subject_only_when_on_the_timetable(title, subject):
    """A "Subject: task" prefix counts only if it names a subject on the timetable (ignoring "Year N")."""
    assert title_subject(title, TIMETABLE.values()) == subject


def test_title_subject_without_timetable():
    """With no timetable subjects known, no title prefix is trusted."""
    assert title_subject("Discovery: Psych Lab", []) is None


def test_title_prefix_used_without_class_match():
    """Without a class on the timetable, a matching title prefix gives the subject."""
    tasks = [{"id": 1, "title": "Discovery: Psych Lab", "addressees": [{"name": "A Student"}]}]
    assert with_subjects(tasks, TIMETABLE)[0]["subject"] == "Year 8 Discovery"


def test_class_match_wins_over_title_prefix():
    """The class's timetable subject is preferred to the title prefix."""
    tasks = [{"id": 1, "title": "Discovery: DJing", "addressees": [{"name": "Class PABC1 B"}]}]
    [task] = with_subjects(tasks, TIMETABLE)
    assert task["subject"] == "Year 8 Performing Arts"
