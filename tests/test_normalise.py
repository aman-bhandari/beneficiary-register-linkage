"""Names written in two scripts and many spellings must reduce to the same keys; the parser must not lose the
given name to a prefix or a community middle name."""
import pytest

from normalise import place_key, split_name


@pytest.mark.parametrize("a,b", [
    ("भगवती देवी बिष्ट", "BHAGAWATI BIST"),
    ("सुरेन्द्र सिंह नेगी", "Surender Negi"),
    ("कमला देवी", "Kamala"),
    ("पार्वती जोशी", "Parbati Joshi"),
    ("मोहम्मद सलीम खान", "Md. Salim Khan"),
    ("हरजीत कौर सन्धू", "Harjit Kaur Sandhu"),
    ("गेंदालाल राणा", "Gendalal Rana"),
])
def test_cross_script_skeletons_agree(a, b):
    x, y = split_name(a), split_name(b)
    assert x["skel_first"] == y["skel_first"], (x, y)
    if x["last"] and y["last"]:
        assert x["skel_last"] == y["skel_last"], (x, y)


def test_prefix_is_not_the_given_name():
    assert split_name("Mohd. Salim")["first"] == split_name("Salim")["first"]
    assert split_name("मोहम्मद सलीम")["middle"] == "md"


def test_first_word_stays_the_given_name_even_if_it_is_a_middle_word():
    assert split_name("Ram Singh Rana")["first"] == "ram"
    assert split_name("Kishan Ram Arya")["first"] == split_name("Kishan Arya")["first"]


def test_suffixes_are_dropped():
    assert split_name("Harjeet Kaur")["last"] == ""
    assert split_name("Kamla Devi Bisht")["last"] == split_name("Kamla Bisht")["last"]


def test_place_keys_keep_wards_and_fold_spelling():
    assert place_key("RUDRAPUR WARD 12") == place_key("Rudrapur Ward 12")
    assert place_key("RUDRAPUR WARD 12") != place_key("RUDRAPUR WARD 13")
    assert place_key("ALISUPYAL") == place_key("Alisupiala")
