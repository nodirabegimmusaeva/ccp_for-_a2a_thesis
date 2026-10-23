# Google Forms reviewer interface

`create_review_forms.gs` is a self-contained Google Apps Script containing the 32
blinded development outputs. No OpenAI API key, private condition mapping, or real
resident records is included. It has not been executed against Google Forms yet.

## Create the forms

1. Open https://script.google.com/ and choose **New project**.
2. Replace the default contents of Code.gs with `create_review_forms.gs`.
3. Save, select **createReviewForms** in the function menu, and click **Run**.
4. Authorize Google Forms access when Google asks. The export function also uses
   Drive to create CSV files; no existing files are deleted or shared.
5. Open the four EDIT links from the execution log. Preview each form, including
   long grids on a phone. All forms start closed to responses.
6. Review and freeze the scoring rubric before formal collection. The existing
   missing full-address criterion has not been silently added to this v1 export.
   Treat this export as calibration until that rubric audit is completed.
7. Publish/enable responses in the Forms UI and configure responder access for
   your reviewers. Do not enable public response summaries. Share responder links,
   not editor links. The script does not grant public access or send invitations.

Each form has a reviewer-code question and eight case sections. Each section shows
original complaint, recorded address, readable final work order, a requirement grid,
overall completion, and required evidence notes. Choices map to pass/fail/uncertain.
Give reviewers distinct codes such as R1 and R2. Each reviewer completes all four
forms independently. Google account requirements depend on your Workspace settings.
No emails are collected by the script.

## Export ratings

Run **exportRatings** after collection. It reads Forms responses and creates a new
Drive folder with one CSV per reviewer, compatible with:

    python3 -m real_llm_comparison.study_tools agreement R1.csv R2.csv

It rejects duplicate submissions for the same reviewer/case and malformed ratings;
it logs completed case counts. Ensure both reviewers have all 32 cases before
agreement. Preserve original independent ratings before adjudication.

Only final compliance/completion is assessed here. Handoff retention requires a
separate instrument showing final-agent inputs, and representation may then reveal
condition. Do not use these final-answer ratings as retention scores.

## Rebuild after rubric changes

    python3 tools/google_forms/build_review_forms.py PACKET.json tools/google_forms/create_review_forms.gs
    node tools/google_forms/test_generator.cjs

The generator reads only the blinded packet. Re-running createReviewForms in the
same Apps Script project reuses completed forms. If creation stopped midway it
stops rather than silently duplicating or deleting the partial form. Inspect that
form and project state before restarting. Use a new version/project for a revised
rubric; do not change an instrument after formal responses begin.

The local mock validates generated structure and rerun behavior, not Google service
permissions, live API execution, or actual UI layout. Preview in Google Forms is
still required.
