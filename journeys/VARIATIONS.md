# Register variations — the differentiation library

## PERFORMANCE NOTES (from measured IG data, updated 2026-08-22 — the refill reads this first)
- **The rethink package works (2026-08-22, n=10 vs 31 earlier posts).** Videos posted since
  2026-08-14 (new-doctrine journeys + music deck + resolve engine): median views 506 vs ~165
  before, pushed >300 views 60% vs 14–29%, >1000 views 40% vs 0–12% (and the only earlier
  >1000s were remix re-posts); pooled like 2.59% ±0.33 vs ~1.95% — better engagement on much
  colder pushed traffic. Followers 34→59 in the 9 rethink days (~2× the earlier growth rate).
  Era/engine/music co-move by construction — this validates the PACKAGE. Keep composing to
  the current doctrine; nothing here licenses relaxing it.
- **Standouts to learn from:** sundew_snare 3.05x qscore (5.2% like at 1410 views — catalog
  best); squid_lantern = biggest organic reach ever (2982); desert_rosette 1.50x at 1373.
  Weakest rethink posts: abyssal_chandelier 0.63x, physarum_maze 0.69x (young — provisional).
- **Dark + saturated wins.** like% correlates: luminance −0.33, saturation +0.24, deep-shadow
  +0.28. Compose worlds on dark grounds with saturated accents; pale high-key washes (pastel
  sugar, frost white, foam, salt flats, pale moss) are the measured bottom quartile. candy_gloss
  is RETIRED.
- **Nameable beats esoteric.** The top performers are instantly-nameable worlds; abstract-math
  realms without a recognizable anchor underperform. Every card should be a realm a stranger
  could name in two words.
- **Length: long > short > medium.** Hypothesis on file: longs win on range/variability, shorts
  on tight coherence, mediums are neither. tier_share now favors long (0.55/0.15/0.30) — keep
  composing SOME mediums so the hypothesis stays testable.
- **Scale range earns REACH (separate axis from likes).** Full-scale journeys got pushed
  (>300 views) 44% of the time vs 10% for narrow spans; cosmic-reaching 33% vs 7% — likely a
  retention mechanism (a full-range dive keeps promising the next scale). LIKES reward the
  palette/subject; PUSHES reward the span. So: L-tier journeys should reach cosmic scale
  (exp ≥ 11), full span (also ≤ −8) preferred — while keeping every card dark, saturated,
  nameable. Narrow-span micro loops stay legal for S-tier spice only.

## DEPTH-SCAFFOLD LIBRARY (resolve-on-approach, 2026-08-14 — engine/scaffold.py)
Realm arrivals into many-instance fields get an animated depth scaffold (journey card field
`resolve: {mode, variant, density, size}` overrides the band default; `resolve: false` opts out):
- **sea** — clumped 3-D scatter (cells, plankton, stars, molecules, diatom drifts)
- **lattice** — perspective ranks; variants: `cubic` · `hex` (close-packed) · `diamond`
  (two interpenetrating sublattices) · `layered` (sheets with gaps, graphite-style).
  Pick the variant from the REAL mineral (halite/galena=cubic, ice/quartz=hex,
  diamond/silicon=diamond, graphite/mica=layered) — extend as new structures are needed.
- **surface** — crowns/blocks/chimneys on an oblique ground (forests, cities, vent plains)
- **web** — connected nearest-neighbour network with junction beads (cosmic web, neurons,
  mycelium); variants welcome (sheet-webs, radial orb-webs, foam edges).
Single-object approaches use the tracker, not a scaffold; seams keep their own treatment.

Raw material for composing journeys. Any register can be swapped for a variant;
scales can be fractional (a third to half an order of magnitude apart is fine —
set `exp` to floats; `dur` is uniform per journey, no per-card lingering). Journeys
are CIRCULAR: the loop target auto-derives from `regs[0]` (no manual last-card
target needed). The seam pair can be
anything — continent→nucleus is legal and encouraged when it's beautiful.

## Cosmological (10²⁰–10²⁶) — geometric/mathematical network plays
- classic irregular cosmic web (filaments + voids)
- Zel'dovich pancake sheets: thousands of galaxies schooling in one doubled-over folding
  sheet with luminous caustic creases (how the web actually forms — a murmuration writ
  cosmic; genuinely different from filament-and-void)
- voronoi foam of glowing cell walls (soap-bubble universe)
- neuron-web (the universe-is-a-brain look: dendrites + synaptic nodes)
- strange-attractor ribbons (Lorenz butterflies of galaxies)
- hyperbolic tiling receding to a glowing rim
- crystalline lattice of galaxy clusters (universe as mineral)
- braided rivers of light / mycelium mat
- reionization bubble froth: the universe's first foam — spheres of first
  starlight swelling through a neutral fog until their walls touch and merge
  (cosmic dawn as soap-froth; genuinely different from filament-and-void)
- intrafilament corridor: riding INSIDE one filament of the web — galaxies
  drifting past like lanterns in a hallway of haze, the voids glimpsed as
  blackness through the filament's walls

## Galaxy (10²¹)
- spiral / barred spiral / ring galaxy / colliding pair
- fractal fern of stars; hurricane of starlight; phyllotaxis sunflower-spiral
- galaxy made of anything: jellyfish light, molten gears, stained glass shards

## Stellar / planetary (10⁷–10¹²)
- classic star + orbits; binary stars; star nursery pillars
- planet variants: ocean world, lava-vein world, banded gas giant, geode planet
  (cracked open, crystal interior), lantern planet (city-light shell)

## Landmass / terrain (10⁴–10⁶) — Lorraine's realm
- striated canyon country (Grand-Canyon bands) · fjordlands · dune seas
- terraced rice-paddy mountains · glacier fields with melt rivers
- patchwork farmland quilts · volcanic calderas · river deltas branching
- forests, jungles, tundra

## City / built world (10²–10⁴)
- vertical tower city · canal city · rooftop-garden city · souk/market maze
- clockwork city · paper city · coral-grown city · city inside a geode
- mountainside cave cities, medieval castle cities
- factories and produdction; formations of people

## Human scale (10⁻¹–10¹) — the richest zone, spend time here
- cluttered desk (lantern, books, clockwork) · workshop · market stall
- dollhouse recursion: a room containing a dollhouse that IS the room
  (self-similar gag, natural fractional-scale steps)
- greenhouse interior · library canyon of shelves · kitchen macro-world
- arcade; theme park ride; pop concerts
- living room scenes (tv is a good way to jump to anothrt scale)


## Creatures (10⁻⁴–10¹) — food-chain chains, fractional steps
- big fish eats fish eats fish… (each ~1/3 decade apart, 3-5 links)
- flea on a dog on a rug in a room (parasite ladder)
- moth → songbird → hawk → roc (predator ladder into fantasy sizes)
- whale-sized sky-creature grazing cloud plankton
- medusae: moon-jelly bell fleets pulsing in a night lagoon · siphonophore
  chain-cities · comb-jelly rainbow paddle-rows

## Flora (10⁻²–10²)
- single blossom → garden → forest canopy; mushroom gill cathedrals
- moss macro-world; kelp forest; roots-as-inverted-trees underground

## Cellular / molecular (10⁻⁸–10⁻⁵)
- classic cell interior; neuron forest; blood-river with cell boats
- folded-protein tangles (canonical molecule look)
- crystal/mineral route: zoom into a geode or snowflake lattice instead of life
- DNA helix canyon; virus geometry (icosahedral guests)
- cubic crysyal lattices and other interesting formations

## Atomic / subatomic (10⁻¹⁵–10⁻¹⁰)
- hazy electron probability clouds; nucleus cluster
- bubble-chamber particle tracks (spirals in fog) — canonical quark look
- cosmic-ray shower cascading; quantum foam boiling; string-loop hairballs
- groups of quarks (visibly up-down-up e.g.) forming hadrons and mesons

## Mathematical / structural patterns for the SMALL scales (Phil 2026-07-31: the key
## differentiator — every journey's micro-realm should look structurally DIFFERENT)
- tilings: Penrose kites-and-darts · aperiodic hat-monotile fields · hyperbolic
  {7,3} tiling shrinking to a rim · Islamic girih star-lattices
- growth/aggregation: diffusion-limited aggregation (ink feathering in water,
  frost fingers) · dendritic snowflake arms · lightning Lichtenberg branches
- automata & fields: Game-of-Life glider fleets etched as glowing glyphs ·
  reaction-diffusion Turing spots/stripes (animal-coat math) · Ising magnetic
  domains flickering · percolation crack-lattices
- waves & resonance: Chladni sand figures on a vibrating plate · standing-wave
  interference lattices · moiré fringes between two drifting grids · caustic
  light-webs (pool-bottom shimmer)
- curves & attractors: Lorenz/strange-attractor ribbon nests · KAM orbit tori ·
  Hilbert space-filling curve as glowing circuitry · knot-theory braids
- fractals proper: Mandelbrot/Julia tendril coastlines · Apollonian gasket foam ·
  Menger sponge canyons · Romanesco phyllotaxis spires
- structure: gyroid & minimal-surface labyrinths (butterfly-wing photonics) ·
  E8/quasicrystal starburst projections · Voronoi shatter · geodesic domes all
  the way down · tesseract/4-D wireframe projections
- flows: laminar streamline foliation (flow-lines combed around obstacles —
  banded glacier ice, comet-tail streams, taffy-pull sheets) · Truchet-tile pipe
  mazes · cycloid/epicycloid rosettes (spirograph gear-flowers) · loxodrome
  spiral shells · Cantor-dust strata (bands whose gaps repeat inside every band)
- folds & forces: Miura-ori crease tessellations (accordion mountain-valley
  fields that fold flat) · catenary chain-net vaults (hanging-chain webs,
  inverted-arch forests) · Lissajous/harmonograph curve nests (pendulum-drawn
  rosettes that never quite close) · force-chain networks in packed grains
  (glowing stress skeletons branching through a granular pile)
- self-carrying structure: reciprocal-frame grillages (Leonardo lattices —
  spiraling beam-rings where every rib rests on its neighbour, no center post:
  water-lily pad vaults, dome centering, basket sunbursts)
- boil & churn: Bénard convection cells (a self-organizing polygonal boil — glowing
  tile-cores seamed by sinking cooler lanes; solar granulation, lava lakes, miso
  soup) · Kármán vortex streets (a staggered procession of paired eddies peeling
  off an obstacle — cloud wakes past islands, flags, chimney smoke)
- USE: pick ONE family per journey and reskin it to the theme (jade-carved
  automata, sugar-crystal Penrose, brass Chladni). Never repeat the previous
  video's family.

## SPACE treated differently every time (Phil 2026-07-31: the space stretch of each
## video must have its own astronomical personality — never default nebula+spiral)
- structures: globular cluster swarm (a million-bee hive of stars) · lenticular
  dust-lane disk · colliding pair with tidal bridges · barred spiral · ring
  galaxy · supernova-remnant lace veil · Herbig-Haro jets from a cradle star ·
  butterfly planetary nebula · pillars-of-creation columns
- exotic physics looks: gravitational-lens Einstein rings and arcs · magnetar
  field-line cages · pulsar lighthouse beams sweeping · quasar accretion disk
  with jet · dark-matter scaffold (ghost-blue web behind the visible) · black
  hole with lensed photon ring (we have black_hole — vary the look if reused)
- planetary-system variety: Saturn's real hexagonal pole storm · aurora curtains
  over a gas giant · Oort comet halo · rogue dark planets with city-fire veins ·
  tidally-shredded moon rings · binary sunset worlds
- painterly modes: ink-wash sumi-e cosmos · stained-glass nebula · embroidery
  stitched starfield · candy-colored accretion swirl — match the journey's theme.
- deep-sky one-offs: light-echo shells around a flared star (nested luminous
  rings lighting up ancient dust, V838-style) · a protoplanetary disk with
  carved gap-rings and a glowing hub · a herd of cometary globules all
  streaming one way like tadpoles fleeing a bright rim
- stellar SURFACES (the under-built band at close range): solar granulation sea —
  the star's face as a boiling tile-field of glowing cells seamed by sinking
  lanes · sunspot archipelago — void-cored islands ringed by combed copper
  filaments · spicule forest — plasma jets standing like wind-combed wheat ·
  coronal loop arcades bridging a spot pair · a supergranule's cell-of-cells
  (granulation nested one order up)
- galactic one-offs: the Magellanic stream — a river of stars and gas bridging
  two dwarf galaxies to a great spiral (a stream you can travel, not a field)

## PALETTE FAMILIES — assign each journey ONE home family so the catalog stays varied
(adjacent cards still contrast in temperature WITHIN the family; the family is the
video's overall color identity)
- candy neon (magenta/cyan/lemon) · jewel tones (ruby/sapphire/emerald on black)
- pastel dawn (peach/lavender/mint) · ember & ash (orange fire on charcoal)
- arctic (ice blues/white/silver) · bioluminescent deep (teal/green glow on black)
- gilded (gold/bronze/verdigris) · ultraviolet noir (violet/electric blue/black)
- monochrome + ONE accent (ivory/obsidian + a single emerald or vermilion) ·
- iridescent pearl (oil-slick rainbow on cream) · sumi-e ink (black/paper + one
  vermilion stamp) · jade & vermilion (celadon/deep green + red-orange)
- mirage (burnt sienna/rose-gold/deep violet dusk) · petrol sheen (oil-slick
  green-violet shimmer on charcoal black)
- abyssal opal (translucent pearl/pale rose/ice blue glowing on navy-black) ·
  cobalt & whitewash (cobalt night/lime-white walls/brass lamplight) ·
  cyanotype (Prussian blue/paper white)
- smoked amber (dark oolong amber/burnt caramel/pale gold lamplight on soot black) ·
  desert rose & turquoise (dusty rose sandstone/turquoise glaze/bone-white plaster)
- olive & terracotta (sun-bleached olive paint/ochre dust/terracotta clay on
  burnt-umber shadow — noon earth-greens, not dusk) · vermilion lacquer & bone
  (glossy vermilion-forward/bone ivory/soot black — red as the SUBJECT, unlike
  sumi-e's single stamp)
- midnight sun (low honey-gold light/teal glacier ice/long violet shadows) ·
  porcelain prism (high-key porcelain whites + prismatic refraction edges — a
  rare BRIGHT family in a night-heavy catalog) · plum & brass (deep plum dusk/
  aged brass/candle amber)
- marigold & indigo (saffron-gold festival bulbs/deep indigo dusk/oxblood
  lacquer — a saturated complementary pair, unlike smoked amber's monochrome
  glow) · absinthe & pewter (pale chartreuse glow/pewter grey/cool smoke — the
  catalog's first green-grey family)
- watermelon tourmaline (rose-quartz pink core/rind-green glow on black — the
  catalog's first pink+green complementary pair) · viridian & bone (deep
  green-lacquered walls/moonlit bone ivory/ghost-blue glass light — dark
  museum green, not absinthe's chartreuse or jade's celadon) · raku
  copper-flash (molten copper-flash red/mottled turquoise crackle/smoke
  black — a ceramic-glaze pair, hotter than petrol sheen)
- oxblood nocturne (moonlit oxide-red earth deepened to oxblood/silver
  grass-glint/pearl star-haze — red earth by moonlight, not mirage's dusk) ·
  garnet furnace (deep garnet-crimson fire/burnt-maroon void shadow/thin gold
  filament highlights — crimson-forward smolder, unlike ember & ash's orange) ·
  moss & mercury (bottle-green moss glow/mercury-silver rain sheen/sodium-amber
  lamp pinpoints — wet-metal green, deeper than absinthe & pewter) · ash &
  roseglow (smoke-blue ash-grey masses/a low rose-ember horizon band/green-violet
  iridescent glints — winter dusk with a starling sheen)
- tokay slate & cinnabar (storm-slate blue-grey field/cinnabar-orange speckling/
  moon-milk pale accents — cool grey-blue carrying hot orange points, no gold
  anywhere) · peat & lily ivory (peat-tea bronze water/moonlit lily ivory/deep
  fern green — an ivory-forward night bloom, unlike viridian & bone's museum
  green) · noble glow (gas-discharge duotone: neon red-orange script/argon
  lilac/rain-slick asphalt grey — signage as the only color source) · alkaline
  rose (spirulina crimson-rose shallows/soda-crust chalk blades/thunder-grey
  volcanic ash — a saturated biological red laid on mineral white)
- RULE: check the last few journeys' families and pick a DIFFERENT one.

## LENGTH VARIETY (Phil 2026-07-31 — the catalog must mix durations)
Three tiers (see journey-composer SKILL for exact bar math): SHORT ≈9s / 4 bars — a tight
realm slice; MEDIUM ≈14-16s / 6-7 bars — a themed roam; LONG ≈26-30s / 11-13 bars — the
epic ladder. Short journeys are perfect for staying INSIDE one realm (all-microscopic,
one interior, one city block); long ones earn the quark↔cosmos traverse. Vary music bpm
on top for further spread. Don't make every journey 8 bars.

## MICROSCOPIC REALMS BY SETTING — micro-worlds hiding in every scene (short-journey fuel)
- **domestic interior**: frost ferns on a winter windowpane · soap-foam voronoi rafts in a
  sink · sugar/salt crystal fields on a counter · steam-bead constellations on a lid ·
  candle-soot dendrites · tea tannin swirls · mold-garden forests on old bread · dust-mote
  galaxies in a sunbeam · carpet-fiber jungles with mites as fauna
- **clothing / fabric**: twill ridge-and-valley weaves · a single dyed fiber's scale bark ·
  velvet pile forests · button nacre · zipper-tooth ranges · dye platelet terraces
- **paper / desk**: paper-fiber felt mats · graphite flake stacks · ballpoint ink braids ·
  eraser crumb boulders · stamp perforation cliffs · pencil cedar grain
- **city exterior**: rust dendrite blooms on railings · verdigris crystal terraces on bronze ·
  asphalt aggregate rubble-fields · concrete air-bubble caves · paint-layer strata cliffs ·
  brick pore canyons · lichen continents on stone · spider-silk cable bridges · pollen dust
  on a bench · neon-tube plasma interiors
- **landscape / nature**: leaf stomata breathing-pore fields · sand-grain jewel heaps (each
  grain a different mineral) · pond-water plankton zoos · lichen/moss micro-forests · spider
  web dew-bead strings · butterfly scale shingles · feather barbule zips · snow crystal fields
- **body-adjacent (non-gory)**: fingerprint ridge canyons · hair-strand cuticle shingles ·
  tear-salt crystal stars on glass
- **music objects**: vinyl groove canyons with engraved waveform walls · the stylus diamond
  prow riding the spiral · speaker-cone paper craters · wound guitar-string coil ridges
Each of these can BE a whole short journey (establish the human-scale scene → dive to its
micro-realm → seam back out) — the micro world is the destination, not a waypoint.

## NON-COSMIC SEAMS + realm-local loops (escape the quark-fuzz→galaxy-fuzz cliché)
A seam just needs the same VISUAL STRUCTURE read at two scales. Ways home that never touch space:
- pattern → the same pattern writ large in the ORIGIN scene: ice lattice → the frost-fern
  "forest" on the same windowpane · rust dendrite → the river delta on a map poster · foam
  micelles → the soap-bubble raft in the sink you started at
- texture → landscape: fabric weave → terraced fields · paper fibers → birch forest ·
  concrete bubbles → cave country · crystal cleavage steps → canyon terraces
- image-carrier jumps (human-made portals): a TV/phone screen's phosphor grid → the scene it
  displays · a painting's brushstroke ridges → the painted landscape · a map's contour lines →
  the coastline itself · a snow-globe interior → the real blizzard outside
- creature-scale folds: pollen sphere → the tree canopy that shed it · a dew bead on silk →
  the whole web at dawn · butterfly-scale shingles → a roofscape of clay tiles
- glowing-things-as-sky: glowworm cave ceilings, city lights from above, lantern gardens,
  plankton wakes — any of these can PLAY the "cosmos" role so the journey never leaves its
  world. Genuinely different from yet another galaxy.
- quantum foam ↔ cosmic web (canonical)
- cell organelles ↔ nebulae
- dollhouse ↔ real house (self-similar loop at human scale)
- geode interior ↔ star field; eye iris ↔ spiral galaxy; coastline ↔ leaf edge
- any small round object like theball on the end of an insect antennae could become a planet
- clouds over a landmass becoming a fog can become almost anything: nebulae, quantum or cosmological "fogginess"
- at astronommical levels, can deissolve into "black hole" (use appropriate lensing) and come out in humanish realm, e.g.
- tv or phone screens can be a segue from human scale to any other


## Journey-idea: trending-sound-driven (Phil, 2026-07-28) — TikTok-exclusive
Reverse the flow: pick a currently-trending TikTok sound (esp. one with lyrics/voice/a
hook), then CRAFT a journey around that sound — sync the dive's beats/plunges to the
track, maybe let a lyric cue a scene. These would be TikTok-only (commercial-sound rights
+ the trend is TikTok-native). Revisit when composing journeys; worth testing if we can
make a sound→journey pairing land. (Everything else = our own custom-generated music.)
