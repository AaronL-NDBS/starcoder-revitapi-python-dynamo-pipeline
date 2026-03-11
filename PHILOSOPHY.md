# Philosophy & Intent

## Why this project exists

I'm a Mechanical Designer by trade, with a multi-year background in AutoCAD,
SolidWorks, Inventor, and Fusion 360. For the past three years I've been working
primarily in Revit, and the learning curve coming from an AutoCAD-heavy background
has been steep — but worth it.

Stumbling onto Dynamo and its automation capabilities opened a whole new world of
possibilities. I've spent hours learning it and can now comfortably produce my own
node graphs for tasks I find tedious — graphs I can reuse across multiple projects.

Then came another discovery: Dynamo can run Python scripts that interact directly
with the Revit API, often more efficiently than thirty nodes chained together.
That changed how I think about automation entirely.

Mixed in somewhere along the way, I started asking AI models to help me build
Dynamo node graphs or fix problems I was stuck on. Success rates were generally
low. Eventually I shifted to asking for Python script nodes that plug into Dynamo
using the `IN[]/OUT` pattern and call the Revit API directly. Success rates
improved noticeably — and that observation is what this project is built on.

---

## The problem this addresses

Revit is a powerful tool with a lot of amazing features. But it only takes a few
internet searches to find a long list of complaints about functionality that is
missing, underdeveloped, or just not intuitive. These issues aren't baseless, 
it's not uncommon for me to be working on something and wish Revit had a
built-in, intuitive solution.

This project is an attempt to fill some of that gap — through a locally-deployed,
fine-tuned version of StarCoder2 that understands the Revit API and Dynamo Python
conventions well enough to be a genuine starting point. Not a finished answer, but
a reliable first draft that someone with domain knowledge can verify and extend.

---

## On using AI to build this

I'll be straightforward: I don't have a strong coding background. I understand
what this pipeline needs to *do* — scrape forums, clean data, format training
pairs, filter for quality — but I don't have the coding/python fluency to write it
from scratch in a reasonable timeframe.

I have a day job. I have a family. The hours I can put toward a side project are
limited, and I'd rather spend them on the domain I actually understand — Revit,
Dynamo, BIM workflows — than on learning web scraping internals or fine-tuning
infrastructure from the ground up.

So I used AI — primarily Anthropic's Claude — to help design and write the
majority of the code in this repository. I described what I needed, pushed back
when something didn't match my understanding of how Revit or Dynamo works, and
made the decisions about architecture, scope, and tooling. The code is
AI-generated. The judgment calls are mine.

I think that's a legitimate way to build something. The alternative isn't
*"Aaron writes this himself"* — the alternative is it doesn't get built at all.

---

## What I bring to this

The value I contribute isn't the Python. It's knowing:

- Why the `IN[]/OUT` pattern matters and how Dynamo actually executes nodes
- Where the Revit API is unintuitive and where common examples are just wrong
- Which forum threads are worth scraping and which are noise
- What a good Dynamo Python node looks like versus one that will silently fail
- The coordinate system and linked model pitfalls that trip up even experienced
  Revit users

A model trained on this data without someone who understands the domain would
produce plausible-looking but unreliable output. The domain knowledge is the
contribution.

---

## A note on transparency

I've disclosed AI involvement in the `NOTICE` file as required by the Apache 2.0
license, and I'm stating it plainly here because I think it's the honest thing to
do. If you use this project, you should know what it is: a domain-informed
pipeline built with AI assistance by someone who genuinely cares about the problem
it's trying to solve.

If you work in Revit and Dynamo and want to contribute cleaner training data,
better prompt/completion pairs, or corrections to the scraping logic — that kind
of contribution is exactly what would make this more useful.
