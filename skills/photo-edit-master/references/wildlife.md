# Wildlife

Use with the workflow in `SKILL.md` when an animal's presence, behaviour or relationship with its habitat carries the photograph. The goal is an animal with presence in a world that supports it: the eye goes to the animal, then to what it is doing, then to where it is.

## Decide the picture type first

| Type | What carries it | Typical treatment |
| :-- | :-- | :-- |
| **Portrait** (head or half body fills the frame) | Eye, face, texture | Tight crop with gaze room. Strong subject/background separation, eye dodge, dark or smooth background, texture on feathers or fur. |
| **Action** (flight, landing, catch, fight) | Gesture and moment | Crop for direction of travel. Keep all of the wing tips, feet and prey. Freeze the peak; spray and droplets are part of the moment. |
| **Behaviour / interaction** | Two or more participants and the space between them | Keep every participant readable. Tone the space between them down without losing it. |
| **Animal in habitat** | Scale and place | Wide crop. Tone the habitat as a landscape (gradients, depth); the animal stays the brightest or most contrasty element at its scale. |
| **Graphic / silhouette** | Shape against light | Commit to the silhouette: deep blacks, clean sky gradient, no shadow lifting. Monochrome is often stronger. |

## Standard moves

1. **Subject mask and its inverse.** Select the animal, including prey or perch if they belong with it. A depth-based selection follows the silhouette and leaves openings such as an open beak out of the subject. Refine its edge with matting when the animal stands clear of everything else in depth; when water, ice, a perch or foreground sits at the same depth, intersect it with an AI subject selection. (In RapidRAW: a Marigold depth mask, `refine_mask` matting, or a depth mask intersected with the subject mask.)

   Look at the mask before grading: on black-and-white birds, AI selections often drop the white shoulder or tail, the beak, the eye or the prey, and a depth band can lose a tail or far wingtip. Add include points or brush them in, then duplicate the finished selection inverted for the environment.

   Keep the edge honest. When the subject is lifted and the surroundings are darkened, any band between the two masks receives neither edit and reads as a halo, worst where the source already has a soft or out-of-focus patch next to the subject. Pull the subject mask slightly inside the animal (a small negative grow and a few pixels of feather; the scale depends on the editor) rather than letting it spill onto the background; an edit that stops just inside the edge is less conspicuous than one that stops outside it. Build the environment as the inverse of that same mask so the two share one boundary. If a rim still shows at 100%, burn a narrow band along that stretch of edge instead of widening the subject mask.

   Common mask mistakes: inverting a mask inverts everything it contains, so "region A except the subject" is A added with the subject subtracted, not an inverted mask. A linear gradient applies its adjustment on one side of its line only; check the overlay before grading. Compare the finished edit with a render that has only the global adjustments applied and look at every outline where the two differ.

   Check the lifted subject's brightest parts at 100% with the clipping view: sunlit folds and whites clip first. Measure the subject against the brightest background area (snow, sky); the animal should stay the brightest element, so ease the environment before darkening it hard, since a heavy darkening merges trees and sky into one flat mass.

   On the subject: exposure up, shadows up, a little texture, a little warmth. On the environment: exposure down, saturation down, clarity down, slightly cooler. Adjust both until the animal separates at thumbnail size.
2. **Eye.** If the eye is visible and sharp, give it a small dodge (+0.2 to +0.4 EV on a small radial or brush) and keep the catchlight. Never paint in a catchlight that isn't there.
3. **Edges.** Burn corners and bright edge clutter. A vignette of −15 to −30 suits most wildlife frames; use radial burns instead when the subject is off-centre.
4. **Crop.** Leave space in front of the face or the direction of travel. Don't clip wing tips, feet or tails at the edge; if the frame does, crop decisively inside the body (at the joint, not the tip) or keep the full frame. Level any horizon or water line.
5. **Detail.** Denoise high-ISO files with dedicated denoise first. Add texture and sharpening to the subject only; keep the background soft.

## Difficult light and plumage

**Dark plumage (eagles, crows, cormorants, dark fur).** Lift the subject's shadows and use texture or clarity to reveal feather structure, but keep the body dark: it should read as a black bird in shade, not a grey one. Protect the white patches (tail, shoulders) with highlight recovery. A darker environment makes a dark animal feel brighter without lifting it.

**White birds on snow or pale sky (swans, cranes, gulls, snowy owls).** Expose for the whites: highlights −30 to −60 and whites down until feather texture returns. Separate white on white with a slightly cooler, darker environment and a touch of warmth on the bird. Snow in shade is blue; keep it blue unless it looks like a cast.

**Blue hour and dusk.** Keep the scene dark and blue. Lift only the animal (subject mask) and any warm light source. Denoise before any lift. The environment usually needs to get darker, not brighter.

**Backlight and rim light.** Keep the rim bright and warm and let the body stay in shadow with just enough detail. Darken the background behind the rim so it glows. Recover highlights in bright water sparkle so the rim still reads as the brightest light.

**Overcast flat light.** Flat light is where local shaping matters most. Build a light direction with a subject dodge on the side facing the brighter sky, burn the far side and the edges, and add colour contrast (warmer subject, cooler surroundings).

**Water and ice.** Blue ice gains depth from a slightly deeper, more saturated blue; keep whites clean. Reflections should be darker than what they reflect. Calm water behind a subject can be darkened to near black for a clean stage.

## Cleanup in wildlife

Remove bright specks, out-of-focus branches crossing the edge of the frame, and distant birds that make a tangent with the subject. Keep perches, prey, droplets, snowfall and other animals that are part of the behaviour. When the photograph is presented as documentary, don't remove anything that changes what happened, such as bait, fences or people in the scene.

## Honesty limits

Tone, colour and crop can be expressive. Don't add catchlights, feathers, anatomy, animals or behaviour. Don't reshape an animal. Emotion comes from gesture and light; don't claim what the animal felt.
