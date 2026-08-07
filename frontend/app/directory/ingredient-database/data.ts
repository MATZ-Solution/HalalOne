// Representative Ingredient & E-Number dataset. The original design loaded this
// from an external `ingredients-data.js`; recreated here as typed data.
// Reference only — verify against the latest cert-body guidance.

export type CertRuling = "Halal" | "Haram" | "Depends" | "Doubtful" | "—"

export type Ingredient = {
  enumber: string
  name: string
  aka?: string
  category: string
  status: string // "Halal" | "Haram" | "Depends on source" | "Doubtful"
  sources: string
  reason: string
  notes: string
  certs: { JAKIM: CertRuling; IFANCA: CertRuling; SANHA: CertRuling; ESMA: CertRuling; MUI: CertRuling }
}

export const INGREDIENTS: Ingredient[] = [
  {
    enumber: "E100",
    name: "Curcumin (Turmeric)",
    aka: "Turmeric yellow",
    category: "Colour",
    status: "Halal",
    sources: "Plant-derived (turmeric rhizome).",
    reason: "A natural plant pigment with no animal or alcohol involvement; halal in its standard form.",
    notes: "Watch for liquid preparations where the carrier solvent should also be halal.",
    certs: { JAKIM: "Halal", IFANCA: "Halal", SANHA: "Halal", ESMA: "Halal", MUI: "Halal" },
  },
  {
    enumber: "E120",
    name: "Cochineal / Carmine",
    aka: "Carminic acid, Natural Red 4",
    category: "Colour",
    status: "Doubtful",
    sources: "Extracted from the dried bodies of the cochineal insect.",
    reason: "Insect-derived; scholars differ on the permissibility of insect-based colourants, so rulings vary by body.",
    notes: "Some certifiers treat it as permissible, others avoid it — confirm the specific product's certification.",
    certs: { JAKIM: "Doubtful", IFANCA: "Halal", SANHA: "Doubtful", ESMA: "Depends", MUI: "Doubtful" },
  },
  {
    enumber: "E441",
    name: "Gelatine",
    aka: "Gelatin",
    category: "Gelling agent",
    status: "Depends on source",
    sources: "Animal collagen — bovine, porcine or fish.",
    reason: "Halal only if from halal-slaughtered animals or fish; haram when porcine or from non-halal slaughter.",
    notes: "The single most source-critical additive. Always verify the animal source and slaughter method.",
    certs: { JAKIM: "Depends", IFANCA: "Depends", SANHA: "Depends", ESMA: "Depends", MUI: "Depends" },
  },
  {
    enumber: "E471",
    name: "Mono- and diglycerides of fatty acids",
    aka: "Glyceryl monostearate",
    category: "Emulsifier",
    status: "Depends on source",
    sources: "Made from plant or animal fats.",
    reason: "Halal when plant-derived; haram when sourced from pork fat. Source is not shown by the E-number alone.",
    notes: "Extremely common in baked goods and confectionery — confirm plant vs animal origin.",
    certs: { JAKIM: "Depends", IFANCA: "Depends", SANHA: "Depends", ESMA: "Depends", MUI: "Depends" },
  },
  {
    enumber: "E422",
    name: "Glycerol",
    aka: "Glycerine, glycerin",
    category: "Humectant",
    status: "Depends on source",
    sources: "Plant oils, synthetic, or animal fat.",
    reason: "Halal when plant-based or synthetic; requires verification when animal-derived.",
    notes: "Widely used as a sweetener and moisture-retainer; check the manufacturer's source.",
    certs: { JAKIM: "Depends", IFANCA: "Depends", SANHA: "Depends", ESMA: "Halal", MUI: "Depends" },
  },
  {
    enumber: "E631",
    name: "Disodium inosinate",
    aka: "IMP",
    category: "Flavour enhancer",
    status: "Depends on source",
    sources: "Often from meat or fish; can be produced by fermentation.",
    reason: "Halal if from fermentation or halal animal sources; doubtful when from non-halal meat.",
    notes: "Common in savoury snacks alongside E627; confirm the production route.",
    certs: { JAKIM: "Depends", IFANCA: "Depends", SANHA: "Doubtful", ESMA: "Depends", MUI: "Depends" },
  },
  {
    enumber: "E153",
    name: "Vegetable Carbon",
    aka: "Carbo medicinalis vegetalis",
    category: "Colour",
    status: "Halal",
    sources: "Charred plant material.",
    reason: "Plant-based carbon black; permissible when confirmed vegetable in origin.",
    notes: "Rare animal-charcoal versions exist historically — modern food-grade is plant-based.",
    certs: { JAKIM: "Halal", IFANCA: "Halal", SANHA: "Halal", ESMA: "Halal", MUI: "Halal" },
  },
  {
    enumber: "E1105",
    name: "Lysozyme",
    aka: "—",
    category: "Preservative",
    status: "Halal",
    sources: "Typically from egg white.",
    reason: "Egg-derived enzyme; halal as eggs are permissible.",
    notes: "Used in some cheeses; egg allergen relevant but not a halal concern.",
    certs: { JAKIM: "Halal", IFANCA: "Halal", SANHA: "Halal", ESMA: "Halal", MUI: "Halal" },
  },
  {
    enumber: "E904",
    name: "Shellac",
    aka: "Confectioner's glaze",
    category: "Glazing agent",
    status: "Doubtful",
    sources: "Resin secreted by the lac insect.",
    reason: "Insect-secretion based; permissibility debated, and residual insect content is a concern for some bodies.",
    notes: "Used to glaze confectionery and coat tablets; rulings differ.",
    certs: { JAKIM: "Doubtful", IFANCA: "Halal", SANHA: "Doubtful", ESMA: "Depends", MUI: "Doubtful" },
  },
  {
    enumber: "E920",
    name: "L-Cysteine",
    aka: "Dough conditioner",
    category: "Flour treatment",
    status: "Depends on source",
    sources: "Human hair, duck/poultry feathers, or synthetic.",
    reason: "Halal when synthetic or from halal poultry; haram/doubtful when from human hair or non-halal sources.",
    notes: "Found in some breads and bagels — source disclosure is essential.",
    certs: { JAKIM: "Depends", IFANCA: "Depends", SANHA: "Doubtful", ESMA: "Depends", MUI: "Doubtful" },
  },
  {
    enumber: "E1510",
    name: "Ethanol",
    aka: "Ethyl alcohol",
    category: "Solvent",
    status: "Doubtful",
    sources: "Fermentation or synthetic.",
    reason: "Intoxicant alcohol; treatment varies — some bodies permit trace carry-over solvents, others do not.",
    notes: "Context-dependent; a flavouring carrier ruling differs from a beverage ruling.",
    certs: { JAKIM: "Doubtful", IFANCA: "Depends", SANHA: "Haram", ESMA: "Doubtful", MUI: "Doubtful" },
  },
  {
    enumber: "E542",
    name: "Bone Phosphate",
    aka: "Edible bone phosphate",
    category: "Anti-caking agent",
    status: "Haram",
    sources: "Derived from animal bones.",
    reason: "Bone-derived; haram unless from halal-slaughtered animals, which is rarely certified for this additive.",
    notes: "Uncommon in modern products; flagged where present.",
    certs: { JAKIM: "Haram", IFANCA: "Depends", SANHA: "Haram", ESMA: "Depends", MUI: "Haram" },
  },
]
