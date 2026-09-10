# Register variations — the differentiation library

## PERFORMANCE NOTES (measured IG + YT data, updated 2026-09-10 — the refill reads this first)
- **YOUTUBE IS A SEPARATE LOTTERY (2026-09-10, first YT snapshot, n=64).** YT carries 43% of
  our total reach and `corr(YT views, IG views) = +0.04` — essentially zero. The IG-weakest
  videos include YT's biggest: wild_yeast (IG qscore 0.29x, catalog-worst tier) has 1244 YT
  views; salt_mirror (IG 0.10x, catalog worst) has 973. YT is bimodal — median 23 views but
  14 of 64 over 400. NOTHING we currently vary predicts YT reach (duration corr −0.07).
  Implication for composing: do NOT drop a journey idea because it underperformed on IG —
  it may be a YT winner, and the two audiences are not the same people.
- **Parallax gain 1.0 is the best draw so far (n=16).** pooled like 3.28% ±0.39 vs 2.24%
  ±0.20 for pre-parallax (CIs separate); gain 0.9 1.64x qscore (n=2). The low draws look
  bad (0.5 → 0.29x, 0.7 → 0.78x) but are n=1 each. Lean high.
- **Tier L confirmed and strengthened (n=35/19/11).** L 1.35x qscore, pooled like 2.79%
  ±0.22 vs M 1.37% ±0.41 — CIs separate cleanly. S 0.99x, M 0.96x. M remains the weakest
  tier on every cut of the data.
- **Saturation still pays; DARKNESS NO LONGER DOES (n=65).** sat corr +0.19 like / +0.22
  qscore (was +0.34) — same direction, weaker. But luminance is now −0.05 and dark-fraction
  −0.00, where the 08-13 baseline had −0.33 and +0.29. The "dark" half of the two-axis law
  has washed out as the catalog grew: keep the saturation, stop paying for gloom.
- **Weak styles on more data:** crystalline 0.69x (n=4) and reef_pop 0.35x (n=2) sit at the
  bottom; aurora_silk 2.11x and lacquer_pop 1.78x lead but are n=2 each — direction only.
- **zoomout 1.36x vs divein 1.12x** (pooled like 3.16% ±0.41 vs 2.31% ±0.19) — CIs separate,
  BUT zoomout is concentrated in the older era, so this is confounded with era and is a
  candidate for a deliberate test, not a law.

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
- helicoid armor: Bouligand twisted-plywood stacks — fiber sheets each rotated a few
  degrees from the sheet beneath, so the grain descends like a spiral staircase
  (mantis-club and crab-cuticle impact armor; also nacre-adjacent layered shells)
- periglacial sorting: frost-heave patterned ground — sorted stone circles and
  polygon nets self-organized on flats, stone stripes combed down slopes, and
  ice-wedge polygon country seen from the air (the same net at two scales — a
  built-in pattern-writ-large seam that never touches space)
- recursive bisection: a sphere split in half, each half again, each again — a
  raspberry of ever-finer equal cells with the same cut repeated inside every piece
  (early embryo cleavage 1→2→4→8, quadtree tilings, Cantor dust in three dimensions)
- growth-ring annuli: nested concentric rings laid down over time, crossed by radial
  grooves (fish-scale circuli, tree rings, otoliths, agate banding, stalagmite
  cross-sections, ripple rings on a pool) — a timeline read as a target
- hopper stairsteps: skeletal crystal growth where edges outrun faces, so every face is
  a square-spiral staircase descending into itself (bismuth hoppers, halite hopper cubes,
  frost hoppers) — a stepped spiral that rhymes with terraced pits and spiral towers
- Langmuir windrows (added 2026-08-29): floating things combed into long parallel streaks by
  counter-rotating roll vortices under the wind — weed lines on the open sea, foam lanes on a
  lake, leaf-litter stripes on a pond; the same combing at small scale = polymer chains zipped
  side by side, at cosmic scale = galaxies streaming down parallel filaments into a knot
- rouleaux stacks (added 2026-08-29): discs stacked into columns and the columns themselves
  arrayed — coin-stack towers of red cells, the thousand-disc column inside a retinal rod,
  columnar basalt, stacked-plate capacitors, nacre tablet piles; a stack-of-stacks family
  distinct from layered sheets (this is discrete columns, not continuous strata)
- meander & oxbow (added 2026-08-29): a single sinuous channel folding back on itself until
  loops pinch off as crescent lakes — river bends from the air, a zigzag chain kinking at one
  bond, a coiled tube's cut-off loops; the crescent-scar motif repeats at every scale
- core & envelope (added 2026-08-31): exactly TWO parts — a compact bright core wrapped in a
  far wider, fainter sheath (an atom's nucleus in its electron fog, a halo nucleus's tight core
  in its vast two-neutron fog, a galaxy in its dark halo, a lenticular's bulge in its lens, a
  stripped cork bole in its grey cork sheath, an acorn in its cup) — distinct from nested
  shells (many rings) and recursive nesting: two components only; the size ratio is the drama
- helices & screws (added 2026-08-31): ONE line wound around an axis — a bacterium's corkscrew
  flagellum, a dust-devil column, a rattlesnake's coil, tendril and vine coils, a spiral stair,
  a slowly twisting rope-filament of galaxies (the web's filaments measurably rotate) — a
  single-strand family, unlike knot braids (many strands) or loxodrome shells (a surface)
- plume & billow (added 2026-09-03): one fluid falling or bursting through another —
  Rayleigh-Taylor fringes (a dense cloud sinking into a lighter one as a fence of
  descending pillars with curling caps) · mushroom-cap vortex rings · a thrown powder
  burst frozen mid-bloom · cream blooming in tea · supernova ejecta fingers ·
  pyrocumulus towers — the catalog's first turbulence family (billows and curls, the
  opposite number of laminar streamline foliation's combed flow)
- quantized vortex lattice (added 2026-09-03): many identical small whirlpools locked
  into a perfect triangular array — Abrikosov flux vortices threading a superconductor,
  vortex grids in a spinning superfluid, a stirred condensate's whirlpool crystal —
  order MADE of rotation: a lattice whose every site spins (distinct from Kármán
  streets' staggered shed pairs and from cycloid gear-flowers)
- Weaire–Phelan foam (added 2026-09-04): space filled by equal-volume cells of just two
  shapes, every seam meeting at the honest soap angle — the foam that beat the century-old
  Kelvin problem (clathrate ice cages each cradling one trapped gas bead, the Beijing
  Water Cube's wall, an ideal dry foam) — an EQUAL-cell froth, unlike Apollonian's
  every-size nesting or Voronoi's random shatter
- arrested ripples (added 2026-09-04): a travelling wave frozen into a permanent record —
  lithified ripple marks on a slab, stromatolite laminae written by days, varve and
  ice-core banding written by years, baryon-acoustic shells written into the galaxy web
  by the infant universe's sound — parallel wavefronts held still (distinct from
  growth-ring annuli's rings about a center: this is a WAVE stopped mid-stride)
- jackstraws (added 2026-09-06): straight rods thrown down at random and jammed where they
  cross — pick-up sticks, a log jam, the crossed selenite beams of a crystal cave, rutile
  needles crossing at sixty degrees inside a star sapphire, a felt of glass needles, the
  faint crossed tendrils threading a cosmic void — a RANDOM crossed-rod family (distinct
  from lattices, which are ordered, and from reciprocal frames, which are built)
- cages of rods (added 2026-09-06): a hollow walled by parallel ribs — a barrel's staves, a
  birdcage, a lobster pot, a whale's rib arch, the beta-barrel that holds a fluorescent
  protein's glowing point, the filament cage a pulsar lights from inside — the HOLLOW is the
  subject and the ribs are its wall (distinct from foam's closed cells and sponge's
  bicontinuous maze: one open chamber, ribs you can see between)
- helicoidal ramps (added 2026-09-06): stacked flat sheets joined by spiral ramps — a
  multi-storey car park, the endoplasmic reticulum's sheet stacks (Terasaki ramps), the
  "parking-garage" phase of nuclear pasta, a spiral stair threading every floor of a tower —
  sheets AND a helix in one structure (distinct from layered lattices, which never connect
  their sheets, and from helices & screws, which have no floors)
- random-walk scribbles (added 2026-09-06): a path of straight hops joined at random angles
  — a flea's hopping search, a foraging hedgehog's night track, a badger's wandering path
  across a field, the jitter of a pollen grain in water, and the same scribble frozen into a
  polymer's random coil (a rubber protein IS a random walk) — the one family that is both a
  track and a structure
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
- stellar PAIRS and CORES (under-built band, 2026-08-28): the hourglass binary — two
  stars sharing one pinched envelope, a bright stream of gas pouring through the neck
  from the swollen star into the compact one's glowing disk (Roche-lobe overflow; an
  hourglass of fire) · the crystallizing white dwarf — a dying star's core freezing
  from the centre out into a colossal faceted carbon lattice under a thin fog of
  atmosphere · the bipolar butterfly nebula as TWO LOBES pinched at a waist (a dumbbell
  of lit gas, not a ring)
- cosmic-web one-offs (under-built band, 2026-08-28): the great-wall curtain — a sheet
  of galaxies seen nearly face-on, a luminous hanging curtain with the void's blackness
  behind it · the cluster-infall delta — galaxies streaming down several filaments into
  one cluster, a river delta of light converging on its knot · nested-halo froth — dark
  haloes inside haloes, a bubble-within-bubble hierarchy each bubble carrying its own
  small galaxy
- (added 2026-08-31) cosmic-web: the intercluster bridge — ONE filament strung between two
  cluster knots, galaxies beaded down its length, the whole rope slowly twisting; a bridge
  you look ALONG from one knot toward the other, not a field or a corridor · galactic: the
  ragged irregular dwarf — a torn loose scatter of blue star-knots and pink nursery patches
  with no disk and no core (every catalog galaxy so far has been a spiral/bar/ring/
  elliptical/edge-on) · planetary one-off: moonlit river meanders from orbit — silver
  looping channels across a night plain, crescent oxbow lakes glinting, the coast a dark
  scallop (a meander read as a planet's skin)
- (added 2026-09-06) stellar one-offs: the Wolf–Rayet wind bubble — a star that blows its
  own bubble: a near-perfect sphere of lit gas several light-years wide, its rim brightest
  where the wind piles up, the blowing star burning OFF-CENTRE inside it (a bubble with its
  blower, not a shell around a dead star) · the pulsar-wind cage — a torn hollow of ribbon
  filaments wrapped around one point that lights them all from within (the Crab: a lantern
  inside a cage of ribs, not a lace veil) · the runaway star's bow shock — a curved lit bow
  wave standing ahead of a fast star ploughing through a nebula, the wave's wings trailing
  back on both sides (one thing outrunning its own ripples) · cosmic-web one-offs: the
  void's ghost web — inside a great void, a faint MINIATURE web of dwarf galaxies threading
  the emptiness, a web nested in the web's own hole (voids are not empty; they hold a thin
  sub-web of their own) · fingers of God — galaxy clusters drawn out into luminous radial
  needles that all point at the viewer, a sky of spines converging on the eye (the
  redshift-map picture; a needle-burst at the largest scale)

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
- phosphor & bakelite (oscilloscope-green trace glow/bakelite brown-black/one
  vermilion indicator point + dial-lamp amber — instrument-panel light as the
  only color source; greener and warmer-dim than noble glow's street neon)
- bog iron & spawn jelly (rust-orange bog-iron water/clear jelly with cool moonlit
  grey-teal glints/a new-leaf yellow-lime accent on ink black — a spring pool at night,
  iron-stained, not peat & lily ivory's bronze tea) · wine-dark & verdigris (deep
  wine-red garnet grains/verdigris-green brass patina/cold moon-silver on tar black —
  red grains carried by a green metal, unlike garnet furnace's crimson-on-gold) ·
  sockeye & slate (sockeye crimson bodies/wet slate blue-grey rock/foam ivory streaks on
  peat-black water — a moving red on cold grey, no gold) · hemocyanin & tidewrack
  (copper-blue blood glow/tidewrack bronze-brown shells/full-moon silver on wet-sand
  charcoal — a cool blue laid on warm brown) · indigo & saguaro (moon-indigo sky/deep
  cactus olive-teal ribs/one waxy cream bloom + amber eyeshine points on shadow black —
  a desert NIGHT green, not olive & terracotta's noon)
- (added 2026-08-29) sargasso gold & ultramarine (kelp-gold/amber weed masses/moonlit
  ultramarine open water/foam-ivory streaks + copper eyeshine points on abyss black — a warm
  gold laid on cold blue, unlike gilded's verdigris or midnight sun's teal) · cacao & pod flame
  (cacao nib brown-black ground/pod crimson-to-saffron ridge gradients/one raw-bean violet
  accent — the catalog's first brown-forward family; the crimson carries the saturation) ·
  fluorescent duotone (UV-lamp mineral glow: fluorite blue-violet/willemite green/calcite
  red-orange on mine black — three glows and no ambient light at all; cooler and harder than
  ultraviolet noir's electric blue) · bayou eyeshine (paired amber-red eyeshine points/moss-grey
  hanging drapery/black-tea tannin water/pewter moonlight — the only reds are eyes)
- (added 2026-08-31) tree-frog lime & bract scarlet (bromeliad bract scarlet/acid tree-frog
  lime blade glow/tannin-black tank water/silver trichome frost on cloud-forest umber — an ACID
  lime, not jade & vermilion's celadon; the red is a leaf, not lacquer) · cork oxblood &
  magpie azure (freshly-stripped cork-oak bole oxblood-orange/azure-winged-magpie sky-blue/
  dusk-olive canopy/umber pasture on shadow — the catalog's first red-trunk + azure pair,
  nothing gold anywhere) · sorghum bronze & swarm-dust violet (bronze-red sorghum heads/locust
  ochre-brown bodies with straw-yellow hindwing flashes/bruised violet-grey dust sky/marabou
  slate on umber earth — a bronze-red with NO rose-gold, unlike mirage) · prairie afterglow
  (one tangerine afterglow band low on an indigo-black sky/bison-and-mound umber/dusk grass
  gone bronze/lemon owl-eye points — umber-forward, unlike marigold & indigo's saffron festival
  bulbs) · seagrass & cuttle-copper (bottle-green ribbon fields/slate-blue moon-water/
  cuttlefish copper-bronze mottle/moon-ivory sand scars on ink — green-forward and coppery,
  unlike bioluminescent deep's teal glow or hemocyanin & tidewrack's blue-on-brown)
- (added 2026-09-03) gulal magenta & monsoon slate (fuchsia-magenta pigment bursts/deep
  turmeric saffron flares/monsoon slate-blue dusk/oil-flame apricot points on wet charcoal
  lanes — the catalog's first magenta-primary family: saturated powder colour on storm
  grey, no gold, no neon tubing) · krill rose & glacial teal (rose-red swarm bodies/deep
  glacial teal water-black/pale jade glow falling through ice/electric blue photophore
  points — a living red drifting under cold green-blue, unlike sockeye & slate's grey
  rock or arctic's silver) · banksia char & ember vein (char-black stringybark/deep ember
  orange glowing in bark cracks/smoke grey-violet drifts/one acid chartreuse resprout
  accent — night fire ecology, greener and more violet than ember & ash's orange-on-
  charcoal) · helium violet & niobium frost (deep violet-black vacuum dark/frost-silver
  metal tiers/pale cyan discharge glow/one amber indicator point — cryogenic cold-metal
  violet, harder and emptier than ultraviolet noir's electric blue)
- (added 2026-09-04) urchin violet & sunstar rose (deep violet urchin domes/rose-coral
  sunflower-star rays/green-glass water-light on basalt char — a violet-forward benthic
  family, wetter and rosier than ultraviolet noir, no neon tubing) · comet char &
  dicarbon jade (coal-char comet crust/jade-green dicarbon coma glow/cyan ion-tail
  threads on violet-black vacuum — green-on-black colder and emptier than bioluminescent
  deep, no teal water, no amber) · scarab bronze & star-milk (oiled-bronze elytra
  sheen/silver star-milk band on ink-indigo sky/straw-gold grass blades on umber night
  earth — metal bronze under silver skylight, no lamps, no amber glow) · iron dawn
  (rust-red laminated stone domes/ink-blue pre-dawn water/one molten-gold horizon
  seam/silver bead points — a dark saturated dawn, redder than mirage, bluer than
  prairie afterglow)
- (added 2026-09-06) selenite glass & indigo steam (honey-sulfur translucent crystal
  blades lit from within/indigo-black cave air/verdigris-grey steam/one crimson lamp
  point — a LIT-GLASS family: the colour is light passing through stone, not smoked
  amber's brown tea nor gilded's gold metal) · jelly green & tar piling (glass-green bell
  glow/tar-black creosote timber/rust-orange barnacle bands/one cold blue-white dock lamp —
  green glow laid on tar and rust, unlike bioluminescent deep's teal on plain black) ·
  pulsar sapphire & slag ember (sapphire-blue beam light/black-iron slag plates/ember-
  orange fissure glow/rust-violet haze — blue-lit iron with no gold, colder and heavier
  than ember & ash) · sloe & badger-stripe (sloe blue-black thorn shadow/moonlit bone-
  white stripe/hawthorn-red berry points/amber-brown flea shell/one ultraviolet-blue glow
  point — a blue-black night hedge carrying red points, unlike ultraviolet noir's electric
  blue or oxblood nocturne's red earth)
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
