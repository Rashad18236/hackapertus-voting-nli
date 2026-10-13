### Can Apertus read a page image? One request (session 11 step 3d, recorded only)

`scripts/image_check.py` rendered page 8 of `2024_09_22_de.pdf` (the first page of a vote's detailed section, whose
printed heading the parser checks: "Im Detail") as a 72 dpi PNG (53 kB) and sent it as an OpenAI-style image part
with the question "What is the heading of this page?" (00:38 UTC, blablador `vllm-0.23.1rc1`).

The endpoint **accepted** the request (HTTP 200, 1,077 input and 26 output tokens), but the 93-character answer **did
not contain the heading**: Apertus v1.5 8B is a text model, and the answer does not reflect the page. Nothing of the
answer or the page is stored here (booklet text). Page images are therefore no way to check headings with Apertus;
the parser's text checks stay.
