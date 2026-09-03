import os
import image_generator


def test_build_nontechnical_prefers_explicit_image_prompt():
    post = {"format_type": "insight", "topic": "Unity Catalog", "image_prompt": "explicit prompt"}
    out = image_generator.build_nontechnical_prompt(post)
    assert out == "explicit prompt"


def test_get_image_for_post_technical_calls_enhance(monkeypatch, tmp_path):
    called = {}
    # create a dummy raw diagram file the generator will believe exists
    diagram_path = tmp_path / "diagram_raw.png"
    diagram_path.write_bytes(b"PNGDATA")

    def fake_generate_technical_diagram(post_data, output_path="diagram_raw.png"):
        # write the expected file path so subsequent code sees it
        with open(output_path, "wb") as f:
            f.write(b"PNGDATA")
        called["generated"] = True
        return True

    def fake_pollinations_enhance_diagram(diagram_path_arg, topic_arg, domain_arg, output_path="post_image.png"):
        called["enhanced"] = (diagram_path_arg, topic_arg, domain_arg)
        # create output file
        with open(output_path, "wb") as f:
            f.write(b"ENHANCED")
        return True

    monkeypatch.setattr(image_generator, "generate_technical_diagram", fake_generate_technical_diagram)
    monkeypatch.setattr(image_generator, "pollinations_enhance_diagram", fake_pollinations_enhance_diagram)

    post = {"format_type": "insight", "domain": "Databricks", "topic": "Unity Catalog", "text": "x"}
    ok = image_generator.get_image_for_post(post, output_path=str(tmp_path / "out.png"))
    assert ok is True
    assert "generated" in called and "enhanced" in called


def test_get_image_for_post_nontechnical_uses_text2image(monkeypatch, tmp_path):
    called = {}
    def fake_text2image(prompt, width=1200, height=630, seed=None, output_path="post_image.png"):
        called["prompt"] = prompt
        with open(output_path, "wb") as f:
            f.write(b"IMG")
        return True

    monkeypatch.setattr(image_generator, "pollinations_text_to_image", fake_text2image)
    post = {"format_type": "open_to_work", "domain": "marketing", "topic": "career", "text": "x"}
    ok = image_generator.get_image_for_post(post, output_path=str(tmp_path / "out2.png"))
    assert ok is True
    assert "prompt" in called
