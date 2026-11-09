# Spoken voice: make the script sound like a person

The voice-over reads your text literally. Text that looks fine on a page sounds stiff in a mouth. `scripts/voice_lint.py` (run by `spec_lint.py`) flags the worst cases; this file is the reason behind each rule. Read it before writing lines, not after the warnings.

## Write for the ear
1. **Contract.** "I'm", "don't", "it's", "she'd". A full form ("I am not") only for stress, and then once.
2. **Short words, concrete nouns.** "She paid the rent" beats "She fulfilled her financial obligations". Name the object: a blue envelope, not "a document".
3. **One idea per sentence, 5-9 words.** Vary it: a one-word line ("Again."), a medium line, and every few lines one that runs on with "and" the way people do when they are in the middle of a thought.
4. **Fragments are fine.** "Two a.m. Phone still lit." People do not speak in complete sentences.
5. **Numbers as words** (the TTS misreads digits); put the numeral on screen as a `hud` chip.

## Show, then say less
6. **No emotion labels.** "She felt anxious" tells; "She read the text twice and put the phone face down" shows. The linter counts labels.
7. **No lecture.** The narrator never says "the lesson is". Let an event carry it, or let a character draw the wrong conclusion and pay for it.
8. **Specific beats general.** One true detail (the third coffee, a sticky note that says *ask about raise*, the 41 unread) makes a person; a trait ("she was overworked") makes a diagram.
9. **Stock phrases are a tell.** "Let's dive in", "imagine this", "here's the thing", "not just X, but Y", "journey", "a stark reminder". Cut them. If the line still works, it was filler; if it falls apart, there was no content.

## Dialogue
10. **People want something and dodge.** Every exchange: A wants X, B avoids it. If both just report facts to each other it is exposition ("As you know..."): cut it.
11. **Answer short.** A question gets one word, a shrug, a counter-question or silence. A 15-word answer to a question is a speech.
12. **Give each voice a handle.** One habit each: the boss finishes people's sentences, Lena apologises first, the friend jokes when it hurts. Lines should be unmistakable with the names covered.
13. **Interrupt and trail off.** At least a quarter of the lines are short, cut off ("But I-") or start with a filler ("Well," "Look," "Okay.").
14. **Subtext.** "Did you eat?" can mean *I'm worried about you*. Say the small thing, show the big one.

## Rhythm of a film
15. **Questions are hooks, not a tic.** Under a quarter of the narration may be rhetorical questions; answer the rest with a fact.
16. **Do not start five lines the same way.** Three in a row is a device, five is a habit.
17. **Repeat a word only on purpose.** If a long word appears every few lines, use the thing's own name or a pronoun.
18. **Read it aloud, once, at speaking speed.** Wherever you breathe in the wrong place or run out of air, the line is wrong.

## Vietnamese
- Kể như người Việt nói, không dịch từ tiếng Anh: bỏ "một cách", "thông qua việc", "hãy tưởng tượng", "hành trình", "vô cùng quan trọng".
- Lời thoại có từ đệm theo tính cách (à, nhé, đấy, thôi, hả, chứ, nhỉ), xưng hô đúng quan hệ (anh/chị/em/mày/tao, không "tôi - bạn" cho mọi cặp).
- Câu ngắn, từ cụ thể (cái phong bì xanh, không phải "một tài liệu").

## Check before you hand over
Run `python scripts/spec_lint.py spec.json | grep voice`: a spec with `voice:` WARNINGs is not finished, same as any other WARNING.
