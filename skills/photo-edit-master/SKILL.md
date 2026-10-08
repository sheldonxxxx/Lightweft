---
name: photo-edit-master
description: Direct and critique expressive, portfolio-grade photo edits. Turns lessons from master photographers and darkroom printing into concrete decisions about crop, light shaping, colour and finish, with starting ranges, a tonal-hierarchy check and genre guidance for wildlife, landscape, nightscapes, people and still life. Use when planning, executing through an editor skill, or reviewing a photo edit.
---

# Photo Edit Master

Make the photograph a viewer stops for. A technically clean correction that looks like the camera file with a little more contrast is an unfinished edit, not a safe one.

This skill decides **what the finished photograph should look like and which moves get it there**. Pair it with an editor skill (for example `rapidraw-mcp` from the [RapidRAW MCP fork](https://github.com/sheldonxxxx/RapidRAW)) that executes those moves, and with `photo-style-builder` when a personal profile, accepted edits or earlier feedback exist. Current user instructions and the user's accepted edits outrank everything here.

## The standard: print it, don't process it

The masters treated the print as interpretation, not correction. Ansel Adams described the negative as the score and the print as the performance, and his printing notes for *Moonrise, Hernandez* show extensive dodging and burning of sky and foreground. Burning in the edges was routine in fine darkroom printing. Treat each photograph the same way:

1. **Visualise the final print first.** Before any adjustment, write two sentences: what the viewer sees first, what they feel, and where the light falls. Name the tonal key (low-key, high-key or full-range) and the colour idea.
2. **Shape the light by region.** Global sliders set the base. The image is made with local work: subject lifted, surroundings subdued, edges burned, light paths emphasised.
3. **Judge the result as a picture on a wall or a phone screen**, not as a set of plausible adjustments.

Default to decisive. If you can't tell the edit from the RAW at thumbnail size, it isn't finished. Restraint is a choice you make for a reason you can name ("this fog is the subject"), not a default.

## Lessons from the masters, as editing moves

| Lesson | Master | What to do in the edit |
| :-- | :-- | :-- |
| Visualise, then place tones deliberately | Ansel Adams | Decide which areas are the deepest black, the brightest white, and where the subject sits. Set blacks and whites on purpose; don't leave the file's default range. |
| Light the subject, let the world fall away | Rembrandt, chiaroscuro painting | Make the subject the brightest, highest-contrast, most detailed area. Let the surroundings fall off in brightness and clarity towards the edges. |
| Burn the edges | Darkroom printing tradition | Darken the frame edges and corners so the eye stays inside. Keep it subtle enough that the vignette itself isn't visible. |
| Warm against cool | Galen Rowell (*Mountain Light*) | Build colour contrast. Keep warm light on the subject against a cooler environment, or a single warm accent in a cool field. Don't neutralise it away. |
| Simplicity and negative space | Michael Kenna, Vincent Munier | Remove, crop or tone down anything that competes. Empty space works when its tone is even and quiet. |
| The animal in its world | Frans Lanting | Keep habitat that tells the story, but give it less brightness, saturation and texture than the animal. |
| Portrait presence | Nick Brandt | For close animal portraits, commit to a strong tonal key. Deep, clean backgrounds and luminous eyes work; monochrome can sharpen the gesture. |
| Geometry carries the moment | Henri Cartier-Bresson | He composed in the viewfinder and rarely cropped. When the camera frame missed, use the crop to restore that geometry: direction of travel, gaze room, strong diagonals, a clean border. |

These describe widely documented working practices, not looks to imitate. Use the lesson when this photograph gives it a reason. For deeper background, read [learning from the masters](references/master-studies.md).

## Workflow

Work through these steps in order. Steps 2–5 are where average edits usually stop short.

### 1. Read the photograph (brief, written)

- **Subject and story:** who or what, doing what, in what place.
- **Light:** direction, quality, colour, and the time of day it actually shows. A blue-hour scene must stay blue hour.
- **Strength:** the best thing already in the frame.
- **Obstacles:** what stops it being a great picture (flat light, bright clutter, weak crop, colour cast, noise, tilted horizon, a distraction).
- **Final-print sentence:** the visualisation from above.

### 2. Geometry first

Make a crop decision on every photograph. Keeping the full frame should be a decision, not an omission.

- Level horizons and water lines. Straighten verticals when they're meant to be vertical.
- Place the subject deliberately. Leave space in the direction of gaze or travel. A rule-of-thirds position is a starting point, and centring works for symmetry and frontal stares.
- Trim edges that carry clutter, bright patches, cut-off objects or dead space.
- Don't crop so tight that the subject loses its world or the image loses resolution for its intended use. A crop that keeps less than about 40% of the frame needs a reason.
- Choose the aspect for the picture (3:2, 4:5, 16:9, 1:1). Keep the original aspect across a series unless a frame demands otherwise.

### 3. Base: white balance and tonal range

- **White balance serves the mood**, not a grey card. Warm the golden hour. Keep blue hour and snow shade blue. Correct a colour cast only when it fights the story; tints such as teal water or green skin are usually casts.
- **Don't brighten dim scenes by default.** Place the subject's brightness, then let the rest follow. Lifting exposure globally is the fastest way to flatten mood and reveal noise.
- Set the black and white points so the picture has a real black and a clean highlight. Pull highlights to keep texture in white feathers, snow and sky.
- Keep global contrast moderate. Contrast between regions comes from step 4.

### 4. Shape the light (the main work)

Build the brightness hierarchy with local adjustments. For any subject against an environment, the default structure is:

| Region | Typical move (starting range) | Purpose |
| :-- | :-- | :-- |
| Subject (subject or depth selection) | +0.15 to +0.6 EV; shadows +5 to +20; texture/clarity +5 to +20; slight warmth | Presence and detail |
| Environment (the same mask, inverted) | −0.3 to −1.0 EV; saturation −10 to −30; clarity −5 to −20; slightly cooler | Quiet, depth, separation |
| Key area (eye, face, point of contact) | Small radial or brush: +0.1 to +0.4 EV | The first place the eye lands |
| Frame edges | Vignette −10 to −35, or radial/linear burns −0.3 to −0.8 EV | Keeps the eye inside |
| Sky / far background / bright foreground | Linear gradient −0.3 to −1.0 EV, with a wide soft transition so no band shows | Balance the frame; add depth |
| Light path (rim light, sunlit water) | Brush or gradient +0.1 to +0.4 EV, warmer | Tells where the light comes from |
| Pale mass under or behind the subject (ice mound, rock, sand) | Feathered radial, about +0.4 EV worked on one frame (try +0.3 to +0.5) | Carries the eye to the subject without a visible mask |

The ranges are starting points in common slider units: EV for exposure, −100 to 100 for the rest. Judge the result, not the number. Stronger moves are fine when edges stay clean. Build masks from the same subject selection so subject and environment share one boundary, then inspect both overlays for halos and missed areas (between feathers, legs, branches).

Keep whatever the subject stands on or touches attached to it. A deep environment cut that swallows the perch, the ice under the feet or the water contact makes the subject float. After any deep cut, look at the support first.

Create depth with atmosphere: far planes lighter and lower in contrast in mist, or darker in a spotlit scene. Separate near, middle and far planes with gradients or depth masks.

### 5. Colour

- **One colour idea per image.** Warm–cool contrast, a single saturated accent, a restrained palette, or monochrome.
- Use HSL to calm the colours that compete (bright greens, oranges in clutter) and to deepen the colours that carry the mood (blue ice, golden light).
- Colour-grade with intent: cool shadows and warm highlights for split light, or a unified tint for mood. Keep skin, fur and plumage believable.
- Vibrance before saturation. Don't raise saturation globally past about +15 without a reason.
- Try monochrome when colour adds nothing: graphic silhouettes, strong gesture, pattern, harsh mixed light. Deliver it as an alternative, not a replacement.

### 6. Detail and finish

- Denoise before sharpening. Use dedicated denoise for high-ISO dusk and blue-hour files; sliders don't match it. Full-strength AI denoise can make feathers, fur and skin look waxy in close portraits; use a partial strength there and inspect at 100%.
- Add texture and sharpening to the subject, not the background. Soft backgrounds should stay soft.
- Glow, grain and lens blur only when they support the key. Keep them subtle enough to go unnoticed.
- Avoid pulling highlights or whites hard on a clipped light source such as a low sun; on a test frame it became a flat grey disc with a visible ring. Lower overall exposure and add contrast instead, so the source stays bright.

### 7. Clean up

Remove or subdue distractions yourself; don't wait to be asked. Match the method to the defect: a smooth, low-contrast flare ghost in clear sky can be neutralised with a feathered radial correction (exposure, tint, saturation) and no inpainting; inpaint structured objects. Candidates are bright specks, cut-off objects at the edges, stray branches crossing the subject, sensor dust, and litter or people that don't belong to the story. Keep whatever explains the moment (habitat, water droplets, prey, snow). Respect explicit keep instructions. Prefer an honest crop over an inpaint when the crop also improves the composition. Inspect every repair at 100%.

### 8. Deliver alternatives

For a new photograph, deliver **two or three genuinely different interpretations**. Use the lead interpretation plus variations in key, colour or crop (for example *natural*, *dramatic*, *monochrome*). Name each one by its idea, and pick the styles that suit the photograph rather than a fixed set: [style and method notes](references/style-and-method-notes.md) records a four-frame wildlife comparison: what each style did and which settings failed. When the user has an accepted style or asks for one version, deliver one strong candidate and keep alternatives internal.

## Check before delivering

Look at every candidate twice: once for technical defects, once as a picture. Use the editor's inspection or region-sampling tools where they exist (for example `inspect_edit` in current RapidRAW MCP source builds), or measure the exported pixels.

**Technical defects: fix these.** They are rarely intended, and they are what makes an edit look processed.

| Defect | What to look for |
| :-- | :-- |
| **Subject mask coverage** | The selection includes every part of the subject: white patches on dark birds, both mandibles, eyes, feet, prey. AI selections often drop high-contrast parts, which then get the background treatment. Background seen *through* the subject (an open beak, the space between legs or feathers) shouldn't get the subject's lift. |
| **Broken local relationships** | Neighbouring parts of one surface (upper and lower beak, a highlight and the plumage around it) keep roughly their RAW brightness relationship. A sharp change across a small feature usually means a mask edge runs through it. |
| **Edges at 100%** | No halo or dark rim hugging the subject, no untouched strips, no noisy lifted shadows, no repair seams. |
| **Unintended casts** | Whites (snow, white feathers) carry the colour of the light you meant, not a side effect of another move. |

**Artistic questions: answer these for this photograph.** They are prompts, not thresholds. A deliberate choice can answer any of them differently; say what you chose and why.

- **Does the subject separate?** Through brightness in either direction (light on dark, or dark on snow), through colour, or through texture and focus. As a reference point, separation by brightness usually reads clearly at a glance from around 1.3× (about a third of a stop), but a camouflaged or high-key picture may want less.
- **Does the frame hold the eye?** Darker edges or corners often help. An even pale field, a subject that reaches the edge, or an open composition may not want them.
- **Is the mood the light's mood?** A dusk or blue-hour scene lifted into daylight has usually lost something. If the edit is much brighter than the RAW, know why.
- **Does it read at thumbnail size?** At about 256 px wide, the first place the eye lands should be where you intended.
- **Is it clearly better than the RAW,** or only different?

Fix defects before delivering. Treat the artistic questions as a conversation with the picture: if an answer surprises you, look again, then either change the edit or keep it and note the reason.

## Common failures

- **Timid globals.** Exposure +0.3, contrast +20 and nothing else produces a brighter, flatter RAW. It is a common reason AI edits look average.
- **Brightening the mood away.** Blue hour turned to daylight, and dusk noise exposed.
- **No separation.** Subject and background at equal brightness, colour and sharpness. The fix is the subject/inverted-environment mask pair, not more global contrast.
- **Uncropped clutter.** Bright edges, tilted horizons, dead space.
- **A spotlight look.** A lifted oval around the subject or a glowing halo. Build from the subject mask and burn the surroundings rather than brightening a circle.
- **Colour casts presented as "style"**, such as teal water, cyan snow or magenta shadows.
- **Every photo the same.** One grade applied to a whole series regardless of light.
- **Over-cleaning.** Removing the habitat, droplets or prey that tell the story.
- **Floating subject.** An environment cut deep enough that the perch, ice or water contact disappears.
- **Grey plate for a sun.** Highlights and whites pulled hard on a blown source.
- **Rim at 100%.** A pale halo around dark edges (wing tips, head) when a subject lift and environment cut are far apart (about 1 EV left one on a test frame) and the mask edge is soft. Shrink the difference and tighten the selection (grow −10, feather 4 worked there), then recheck at 100%.
- **Monochrome that drops the accent.** The colour version depended on a beak, a light or an eye that grey can't carry.

## Genre guidance

Read the reference that matches the photograph's central relationship:

- [Wildlife](references/wildlife.md): animals, birds, behaviour, habitat, dark plumage, white birds and snow, backlight.
- [Landscape](references/landscape.md): place, depth, weather, pattern.
- [Nightscapes](references/nightscapes.md): the starry sky and the land together.
- [People](references/people.md): faces, gesture, groups, mixed light.
- [Still life and material](references/still-life.md): food, flowers, objects, surfaces.
- [Collections](references/collections.md): selecting and sequencing a book, essay or batch.
- [Spherical photographs](references/spherical.md): 360° images and views selected from them.

Also see [style and method notes](references/style-and-method-notes.md) for a wildlife style comparison.

## Personal style and feedback

When a user profile, accepted edits or review comments exist, follow `photo-style-builder` and apply them **as moves**. "Too bright, keep the blue hour" means lower environment exposure and cooler white balance on the next edit, not a sentence saved to a profile. If a correction repeats, add it as one of that user's questions before delivery, kept in their profile rather than in this skill. When the user returns hand-edited versions, study what they changed (crop, masks, vignette, colour) and do that by default next time.
