# Style and method notes

What happened when the same photograph was edited several different ways. Use these notes to choose a style on purpose, set first values, and recognise a failing edit early. Numbers are in RapidRAW MCP units (EV for exposure, −100 to 100 for other sliders); they describe what worked on specific frames and are starting points, not targets.

The comparison covered four RAW frames from one wildlife trip: a small white bird on a dark, out-of-focus field; two large birds far away on pale ice at blue hour; a raptor touching calm water at dusk; and a crane flying across the low sun. Each was edited in three deliberately different styles beside an unedited render, and every candidate was checked at 100%.

This is a small, informal comparison: four frames, one trip, one editor's judgement, one editing application. Treat the findings as hypotheses to test on your own frame, not rules.

## Choosing a style

Style names: *natural luminous* is a gentle subject lift with a mild environment cut; *low-key* is a deep environment cut; *warm over cool* is warm highlights over cool shadows; *muted with accent* is a desaturated environment that leaves the subject's own colour.

| Situation | Styles worth trying | What stood out |
| :-- | :-- | :-- |
| Bright subject on a dark, soft field | Natural luminous, low-key, monochrome | A mild environment cut already separates the subject. Deeper cuts add drama but start to cost the subject's support (see below). |
| Tiny subjects in an empty, single-colour scene | Cropped natural, near-monochrome fog, warm over cool | On the sparse ice frame the crop did more than any slider. Settle the aspect (16:9, 2:1) before the tone work. |
| Dark subject over water with colour accents | Natural, muted environment with accent colour, monochrome | Accent colour (beak, feet) disappears in monochrome; choose monochrome only when the picture works as pattern and gesture. |
| Backlit subject against a blown source | Dark silhouette, luminous glow, monochrome | The source cannot be recovered; the style depends on whether it is a light or a hole. |

## Findings

### Separation: how much environment cut is enough

- A white bird on dark bokeh separated with environment −0.3 EV, highlights −30, a light vignette (−18) and the subject +0.1 EV. This stayed natural.
- Environment −1.3 EV with subject +0.4 gave a striking low-key result, but the perch and feet sank into black and the bird floated. The subject mask covers the animal, not what it stands on, so the support took the environment cut. After a deep cut, check that everything physically holding the subject still reads as attached.
- Trying to widen the AI subject selection to include the perch (large region plus perch points) inverted the selection onto the background. If a support must be protected, use a brush correction on the environment mask, or keep the cut moderate and add depth with a gradient and vignette.
- A subject lift and environment cut that together exceeded about 1 EV left a pale rim around dark wings at 100%. Reducing the difference to about 0.7 EV helped but did not clear it; setting grow −10 and feather 4 on the subject selection of both the subject and environment masks removed it. Check the rim at 100% along wing tips and the head, not at preview size.

### Monochrome

- Monochrome suited white-on-dark and dark-on-water frames: texture and ripple pattern became the picture, and a little grain (amount 15–28, size 25–30) made it feel photographic. Lifted blacks (+10 to +12) gave a film feel on the white bird frame.
- It removed the eye colour and the beak/feet accents that carried the colour version. Pick it knowingly.
- On a backlit silhouette the monochrome version was preferred on that frame, but only after the sun was handled as in the next section.

### Backlit subject and a blown sun

- Pulling highlights (−70) and whites (−40) on a clipped sun turns it into a flat grey plate with a visible ring. Keep highlights near 0 and lower overall exposure (−0.8 to −0.9) with strong contrast (+28), so the sun stays a source and the rim light on the wing edges stays bright.
- A dark sky hides faint flare ghosts. A luminous, lifted treatment makes them more visible, so clean them in that style.
- Smooth, low-contrast ghost discs in a clear sky do not need inpainting. A feathered radial correction centred on each disc (radius about 15% larger than the visible disc, feather 0.9, exposure −0.2 to −0.25, tint +6, saturation −25) made them effectively invisible at 100%. Use inpainting for structured objects, not for smooth gradients.
- Glow and halation (about 10–35 for glow, 25 for halation) suit the luminous style; the silhouette style needed none.

### Blue hour and empty scenes

- A very dark, very blue frame came alive with a crop (about 40% of the frame, 16:9), exposure +1.3 EV, shadows +35, dehaze +8 and a light vignette. Denoise first (dedicated denoise, 0–100 scale, about 80 for ISO 2500); a heavy crop shows noise as well as softness, so treat the result as a screen picture rather than a print.
- Near-monochrome fog (saturation −72, contrast −8, exposure +1.7, a wide 2:1 crop) turned the same scene into a minimal image in which the subjects read as ink marks. The flat contrast is the style; do not add contrast back.
- Colour grading only tints what the white balance leaves behind. With a strong blue cast, warm highlights and cool shadows in the grade were barely visible until the white balance temperature itself moved warm (+18) and left the scene less blue. Set white balance for the amount of cast you want to keep, then grade.
- Light contouring helped: a feathered radial dodge (+0.4 EV) on the pale mound under the birds and a gradient burn (−0.55 EV) along the foreground pulled the eye to the subjects without any visible mask.

### Masks and gradients

- Inspect a gradient's selection before judging the tone change. A hard transition or a burn on the wrong side of the frame can look like a tonal failure when the selection itself is the problem.
- A subject selection can include gaps between spread wing feathers and lift the background inside them, leaving bright wedges between dark primaries. Exclude those gaps from the subject selection, include them in the environment, and recheck at 100%.

For RapidRAW's linear-mask controls and gap corrections, use its [craft guide](https://github.com/sheldonxxxx/RapidRAW/blob/main/skills/rapidraw-mcp/references/craft-moves.md#linear-gradients).

### Detail

- Dedicated denoise at 100 (ISO 3200) left near-black plumage over-smoothed and etched-looking at 100% zoom. Use 60–70 for close plumage, and add grain if it looks waxy.

## What not to do

- Do not draw conclusions from the preview alone; the halo, the lost support and the sun's ring only showed at larger sizes.
- Do not pull highlights on a clipped light source.
- Do not convert to monochrome without checking what colour was carrying.
- Do not widen a subject selection with a large region plus several points on a thin support; check the mask before building on it.
