# Mystery trick catalogue (the night job's source of cases)

Owner decision 2026-11-15: every night's tasks are classic fair-play murder mysteries. What the job learns from the genre is the
**kind of trick**, never a story. The kinds below are the common stock of detective fiction (locked-room taxonomies, alibi
puzzles, the fair-play rules of the Golden Age): ideas, not anyone's plot. A night takes one kind that is `unused`, writes a
NEW case around it (new victim, new place, new suspects, new clues, new twist on the kind) and marks it `used` here with the
task id. Never reuse a kind twice in a week, never two nights in a row with the same detective-scene shape.

Hard rules (also enforced by `scripts/policy_check.py`):
- No existing franchise: no Detective Conan / Case Closed / Sherlock-pastiche names, characters, cases, titles, catch-phrases,
  not even in tags. The genre is free, a specific story is not.
- The death is never shown or described: no blood, wound, weapon on screen, method or cause of death. The puzzle is the door,
  the alibi, the clock, the footprints, the message: not how a person was harmed.
- The trick is a misdirection trick, never a recipe for harming someone. If a kind needs a poison, a weapon or a drug to work,
  it is not used here.
- Fair play: the three clues are shown on screen, named once, and each one is needed in the reasoning.

| id | kind | the impossible situation | clue pattern (three, in plain view) | the harmless trick | status |
|---|---|---|---|---|---|
| T01 | locked room, key inside | a study locked from within, key on the desk | wax or lint on the frame; a fibre on the key ring; a wrong time somewhere | the door locked from outside with a loop; the time faked | used 010-locked-study |
| T02 | footprints in snow, none out | one set of prints going in | a snow-free patch under where he lay; a snowman or car with snow on one side only; dry boots | he died before the snow; the snow erased the killer | used 011-footprints-in-snow |
| T03 | voice alibi | a perfect alibi: his voice heard live at the minute | a click before the greeting; no breath; an untouched drink | a recording on a timer | used 012-voice-alibi |
| T04 | the stopped clock | every alibi fits the time the clock stopped | a stopped watch with unbroken glass; dust on the clock face; a shadow that does not fit the hour | the clock was stopped to move the time | unused |
| T05 | the dying message | the victim left a word or a drawing | the message is in the wrong language, upside down, or on an object only the killer could reach | the message reads differently from the other side or in the other language | unused |
| T06 | the double | a suspect seen in two places | the same coat but different shoes; a hand with the ring on the other finger; a cheerful man who limps in one sighting | an accomplice or a lookalike plus one borrowed coat | unused |
| T07 | the borrowed key / the second door | a room only one key opens | a modern lock on an old door; a fresh scratch on the hinge; a dusty hook | a second entrance used and put back | unused |
| T08 | the mirror and the light | a witness saw the culprit's face | a clock seen reversed; a witness who is left-handed in the telling; a window reflection | the witness saw a reflection, so left and right were swapped | unused |
| T09 | the missing sound | the one thing nobody heard | a dog that did not bark; a door that squeaks but did not; a sleeper who woke after the alarm | the sound was masked by something loud at a known time | unused |
| T10 | the false witness | a witness is sure of the time | the witness' watch is on a different time zone or running fast; a chime at the wrong hour; a shop with its own clock | the witness' clock was set forward | unused |
| T11 | the cold room | the time of death seems fixed by the temperature | a heater on a timer; an open window sealed later; a draught under the door | the room was warmed or cooled to move the time | unused |
| T12 | the weight on the scale | the same object weighs wrong | a ledger total off by a round number; a scale with a hidden extra weight; a package too light | contents swapped before the weighing | unused |
| T13 | the third copy | two identical documents, one is forged | the ink of different dryness; a folded corner on one only; a date written with the wrong stroke order | the copy was made after, from the original | unused |
| T14 | the staged accident | an accident that looks perfect | a shoelace tied differently; a ladder rung with fresh dirt on the wrong side; a candle that burned for the wrong time | the scene was arranged afterwards | unused |
| T15 | the reversed route | a suspect could not have reached the place | a bus timetable of the old year; a bridge closed that week; a short cut known only to locals | a short cut or a train that did not stop | unused |
| T16 | the code on the wall | a series of numbers or letters left at the scene | numbers that are page-line pairs; letters that spell a place when read down; a calendar marking | the code names the next hiding place, which the culprit used | unused |

How a night uses it: read this table, pick the first `unused` kind that fits the night's topic mix, invent the case. When all
are `used`, vary a used kind with a new twist (note "T04 v2") rather than repeating the case.
