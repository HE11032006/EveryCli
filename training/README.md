# Fine-tuning the semantic model

Fine-tunes `paraphrase-multilingual-MiniLM-L12-v2` on EveryCli's own corpus to
improve retrieval on CLI-specific jargon, without touching dataset generation
(that's a separate roadmap item).

## Workflow

1. `python training/build_pairs.py` — builds `training/pairs.jsonl` from the
   current corpus (`everycli/data/commands/*.yaml`), excluding every scenario
   used as ground truth in `eval/confusion_set.yaml`. That file is the
   non-regression gate for the result of step 2, so it must never also be
   training data.
2. Open `training/finetune.ipynb` on [Google Colab](https://colab.research.google.com/)
   (free T4 GPU is enough for this model size and pair count — training takes
   minutes) or run it locally with a GPU. It fine-tunes with
   `MultipleNegativesRankingLoss` and checkpoints to Google Drive so a
   free-tier disconnect doesn't lose progress.
3. The notebook's last cells run `tools/evaluate_confusion.py` against the
   fine-tuned model via `EVERYCLI_MODEL_PATH` and compare it to the baseline
   captured before training. **Only adopt the fine-tuned model if it matches
   or beats that baseline.**
4. Adopt by either publishing the model to a Hugging Face Hub repo and
   updating `MODEL_NAME` in `everycli/infra/semantic_matcher.py`, or bundling
   it into the PyInstaller build (`models/` folder already read by the frozen
   binary path, see `_load_model`).

## Files

- `build_pairs.py` — training pair construction (unit tested in
  `tests/test_build_pairs.py`).
- `pairs.jsonl` — generated training data, versioned so changes are visible
  in review.
- `finetune.ipynb` — the actual training run; manual/interactive by nature.
