// Reference data for the Certification Authority Directory.
//
// `scope` and `recognised` are "·"-separated lists rather than arrays — that is
// how the source data is authored, and `segs()` in ./logic splits them.

export const REGIONS = [
  "SE Asia",
  "South Asia",
  "Middle East",
  "Europe",
  "Africa",
  "Americas",
  "Oceania",
  "East Asia",
  "International",
] as const

export type Region = (typeof REGIONS)[number]

export type Authority = {
  num: number
  name: string
  fullName: string
  country: string
  region: Region
  type: string
  est: string
  standard: string
  scope: string
  validity: string
  recognised: string
  /** Verification portal. Empty string when the authority publishes none. */
  href: string
  /** Display form of `href`. Empty alongside an empty `href`. */
  urlText: string
  records: string
  notes: string
}

export const AUTHORITIES: Authority[] = [
  {
    num: 1,
    name: "JAKIM",
    fullName:
      "Jabatan Kemajuan Islam Malaysia (Department of Islamic Development Mal…)",
    country: "Malaysia",
    region: "SE Asia",
    type: "Government",
    est: "1997",
    standard: "MS 1500:2019; MS 2200:2020 (Cosmetics); MS 2600 (Logistics)",
    scope:
      "Food · Beverages · Pharmaceuticals · Cosmetics · Food Processing · Logistics · Slaughter",
    validity: "1–2 years, renewable",
    recognised:
      "UAE (ESMA) · Saudi Arabia (SFDA) · Singapore (MUIS) · Indonesia (BPJPH/MUI) · Qatar · Bahrain · Kuwait · Egypt · Jordan · Turkey · South Korea · 50+ countries",
    href: "https://www.halal.gov.my/v4/index.php/ms/halal-malaysia-portal",
    urlText: "www.halal.gov.my/v4/index.php/ms/halal-malaysia-portal",
    records: "142,000+",
    notes:
      "World's most internationally recognised halal certification body. JAKIM-certified products accepted in virtually all OIC import markets. MS 1500:2019 is current standard. Maintains public online cert verification portal.",
  },
  {
    num: 2,
    name: "MUIS",
    fullName:
      "Majlis Ugama Islam Singapura (Islamic Religious Council of Singapore)",
    country: "Singapore",
    region: "SE Asia",
    type: "Government (Statutory Board)",
    est: "1968",
    standard: "MUIS-HC-S001 (Halal Certification Standard)",
    scope: "Food · Food Manufacturing · Food Services · Abattoir",
    validity: "1 year, renewable",
    recognised:
      "Malaysia (JAKIM) · UAE · GCC countries · widely recognised for Singapore-origin products",
    href: "https://www.muis.gov.sg/Halal/Halal-Certification/Check-Halal-Status",
    urlText: "www.muis.gov.sg/Halal/Halal-Certification/Check-Halal-Status",
    records: "28,000+",
    notes:
      "Singapore's only government-mandated halal certifier. Rigorous audit standards. Very well recognised across GCC and SE Asia for Singapore-manufactured products.",
  },
  {
    num: 3,
    name: "MUI",
    fullName:
      "Majelis Ulama Indonesia (Indonesian Ulema Council) — LP POM MUI",
    country: "Indonesia",
    region: "SE Asia",
    type: "Religious / Semi-Government",
    est: "1994",
    standard: "SNI 99001:2016; OIC/SMIIC 1:2019",
    scope:
      "Food · Beverages · Pharmaceuticals · Cosmetics · Chemicals · Biological Products",
    validity: "2 years, renewable",
    recognised:
      "Malaysia (JAKIM) · UAE · Saudi Arabia · accepted across all major OIC markets",
    href: "https://www.halalmui.org/muiV2/main/detail/search-product",
    urlText: "www.halalmui.org/muiV2/main/detail/search-product",
    records: "60,000+",
    notes:
      "World's largest Muslim-majority country certifier. From 2019, BPJPH (government body) oversees mandatory halal certification; MUI provides religious fatwa/assessment. MUI label still widely accepted internationally.",
  },
  {
    num: 4,
    name: "BPJPH",
    fullName:
      "Badan Penyelenggara Jaminan Produk Halal (Halal Product Guarantee Orga…)",
    country: "Indonesia",
    region: "SE Asia",
    type: "Government",
    est: "2019",
    standard: "SNI 99001:2016; Government Regulation PP 39/2021",
    scope:
      "All products sold in Indonesian market (mandatory halal cert from Oct 2024 for food)",
    validity: "4 years",
    recognised:
      "Indonesian domestic market mandatory; growing international recognition",
    href: "https://halal.go.id/produk-halal",
    urlText: "halal.go.id/produk-halal",
    records: "Newly operational",
    notes:
      "BPJPH replaced MUI as the government issuing body from 2019. Mandatory halal certification for all food and beverages in Indonesia from October 2024. Importers to Indonesia now require BPJPH-recognised foreign certificates.",
  },
  {
    num: 5,
    name: "CICOT",
    fullName: "Central Islamic Committee of Thailand",
    country: "Thailand",
    region: "SE Asia",
    type: "Government-backed Religious Body",
    est: "1945",
    standard: "THS 24001 (Thai Halal Standard)",
    scope: "Food · Beverages · Food Ingredients · Food Additives",
    validity: "1 year, renewable",
    recognised:
      "Malaysia (JAKIM) · UAE · Saudi Arabia · GCC countries · Egypt · Thailand is top-5 global halal food exporter",
    href: "",
    urlText: "",
    records: "41,000+",
    notes:
      "Thailand is among the world's top halal food exporters. CICOT is the primary recognised body. Provincial Islamic committees also issue certs under CICOT oversight. CICOT-certified products widely accepted in OIC markets.",
  },
  {
    num: 6,
    name: "IDCP",
    fullName: "Islamic Da'wah Council of the Philippines",
    country: "Philippines",
    region: "SE Asia",
    type: "Religious / NGO",
    est: "1973",
    standard: "Philippine National Standard PNS/BAFS 102",
    scope: "Food · Beverages · Food Processing",
    validity: "1 year",
    recognised:
      "Limited — primarily for Philippine exports to Muslim-majority markets",
    href: "",
    urlText: "",
    records: "5,000+",
    notes:
      "One of two main halal certifiers in the Philippines. Growing importance as Philippines expands halal food exports. Philippine Halal Certification Law enacted 2016 under IDCP framework.",
  },
  {
    num: 7,
    name: "MUIB",
    fullName:
      "Majlis Ugama Islam Brunei (Islamic Religious Council of Brunei Darussa…)",
    country: "Brunei Darussalam",
    region: "SE Asia",
    type: "Government",
    est: "1955",
    standard: "Brunei Darussalam Halal Standard (BDHS)",
    scope: "Food · Beverages · Food Additives · Cosmetics · Pharmaceuticals",
    validity: "1–2 years",
    recognised:
      "Malaysia (JAKIM) · GCC countries — Brunei has one of the world's strictest halal standards",
    href: "",
    urlText: "",
    records: "3,000+",
    notes:
      "Brunei operates one of the strictest halal certification systems globally. BDHS closely aligned with JAKIM MS 1500. Brunei's Halal Hub initiative aims to establish it as a major halal food processing and export centre.",
  },
  {
    num: 8,
    name: "PHA",
    fullName: "Pakistan Halal Authority",
    country: "Pakistan",
    region: "South Asia",
    type: "Government",
    est: "2016",
    standard: "PS 3733:2019 (Pakistan Halal Standard)",
    scope:
      "Food · Beverages · Food Additives · Cosmetics · Pharmaceuticals · Animal Feed",
    validity: "1 year",
    recognised:
      "OIC countries — growing international acceptance; GCC countries increasingly recognising PHA",
    href: "",
    urlText: "",
    records: "12,000+",
    notes:
      "Established under Pakistan Halal Authority Act 2016. Pakistan is a major halal meat, dairy, and processed food exporter. PHA certification mandatory for domestic products and for export from Pakistan. Rapidly growing international recognition.",
  },
  {
    num: 9,
    name: "BSTI Halal",
    fullName:
      "Bangladesh Standards and Testing Institution — Halal Certification",
    country: "Bangladesh",
    region: "South Asia",
    type: "Government",
    est: "1985",
    standard: "BDS ISO 22000; Bangladesh Halal Standard (BDS 1532)",
    scope: "Food · Beverages · Food Processing · Seafood",
    validity: "1 year",
    recognised:
      "Regional markets; GCC countries accept for selected food categories",
    href: "",
    urlText: "",
    records: "6,000+",
    notes:
      "Bangladesh is a significant halal food producer and exporter, particularly fish, shrimp, and processed foods. BSTI handles halal certification alongside its broader standards mandate. Growing halal sector.",
  },
  {
    num: 10,
    name: "ESMA",
    fullName: "Emirates Authority for Standardisation and Metrology",
    country: "United Arab Emirates",
    region: "Middle East",
    type: "Government (Accreditation & Standards Body)",
    est: "2001",
    standard:
      "UAE.S GSO 2055-1:2016; UAE.S GSO 2055-2 (Cosmetics); UAE.S GSO 2055-3 (Pharmaceuticals)",
    scope:
      "Food · Beverages · Cosmetics · Pharmaceuticals · Animal Feed · Food Contact Materials",
    validity: "1 year (granted by ESMA-approved Conformity Assessment Bodies)",
    recognised: "UAE domestic market mandatory; GCC standards alignment",
    href: "https://www.esma.gov.ae/en-us/Pages/EServices.aspx",
    urlText: "www.esma.gov.ae/en-us/Pages/EServices.aspx",
    records: "67,000+",
    notes:
      "ESMA does not directly certify — it accredits Conformity Assessment Bodies (CABs) and maintains a list of 100+ internationally recognised halal bodies whose certificates are accepted for UAE import. Halal cert mandatory for all food products in UAE. ESMA expanded scope to cosmetics in 2024.",
  },
  {
    num: 11,
    name: "SFDA",
    fullName: "Saudi Food and Drug Authority — Halal Certification Division",
    country: "Saudi Arabia",
    region: "Middle East",
    type: "Government",
    est: "2003",
    standard: "GSO 2055-1:2015; Saudi Halal Technical Regulation TR 2055",
    scope:
      "Food · Beverages · Pharmaceuticals · Cosmetics · Food Contact Materials",
    validity: "1 year per import consignment",
    recognised:
      "Saudi domestic market — all food imports require SFDA clearance",
    href: "https://www.sfda.gov.sa/en/halal",
    urlText: "www.sfda.gov.sa/en/halal",
    records: "N/A (import approval system)",
    notes:
      "Saudi Arabia is the world's largest halal food importer. SFDA maintains a list of approved foreign halal certification bodies (includes JAKIM, MUI, IFANCA, SANHA, CIBAL, AFIC). Importers need SFDA-approved cert for all food shipments. Does not issue product certificates directly.",
  },
  {
    num: 12,
    name: "GSO",
    fullName: "Gulf Standardisation Organisation",
    country: "GCC (Regional Body)",
    region: "Middle East",
    type: "Regional Standards Body",
    est: "1982",
    standard:
      "GSO 993:2015 (Halal Food Requirements); GSO 2055-1:2016; GSO 2055-2; GSO 2055-3",
    scope:
      "Standards body — Food, Beverages, Cosmetics (standards applicable across all GCC)",
    validity: "N/A — standards body, does not certify",
    recognised:
      "All GCC member states: Bahrain, Kuwait, Oman, Qatar, Saudi Arabia, UAE, Yemen",
    href: "",
    urlText: "",
    records: "N/A",
    notes:
      "GSO is the regional standards body, not a certifier. GSO 993:2015 and GSO 2055 series are the halal standards adopted across all GCC countries. Exporters to any GCC market must comply with GSO halal standards. JAKIM, MUI, and IFANCA certs are accepted across GCC under these standards.",
  },
  {
    num: 13,
    name: "JISM (Bahrain)",
    fullName: "Bahrain National Institute for Standards — Halal Unit",
    country: "Bahrain",
    region: "Middle East",
    type: "Government",
    est: "1989",
    standard: "GSO 993:2015; GSO 2055-1",
    scope: "Food · Beverages",
    validity: "1 year",
    recognised: "GCC countries",
    href: "",
    urlText: "",
    records: "5,000+",
    notes:
      "Bahrain follows GSO halal standards. Accepts certs from JAKIM, MUI, IFANCA, SANHA and other GSO-recognised bodies. Bahrain is increasingly positioning itself as a halal food hub and re-export centre.",
  },
  {
    num: 14,
    name: "JDQS",
    fullName:
      "Jordan Institution for Standards and Metrology — Halal Certification D",
    country: "Jordan",
    region: "Middle East",
    type: "Government",
    est: "1993",
    standard: "JS 1732 (Jordan Halal Standard); GSO 993 alignment",
    scope: "Food · Beverages · Cosmetics",
    validity: "1 year",
    recognised: "Arab countries; OIC markets",
    href: "",
    urlText: "",
    records: "4,000+",
    notes:
      "Jordan has a significant re-export trade in halal products to Gulf markets. JSMO-certified products and JAKIM/IFANCA certs accepted for import. Jordan's free trade agreements create strategic export routes to neighbouring markets.",
  },
  {
    num: 15,
    name: "NFSA (Egypt)",
    fullName: "Egyptian National Food Safety Authority — Halal Unit",
    country: "Egypt",
    region: "Middle East",
    type: "Government",
    est: "2017",
    standard: "Egyptian Halal Standard ES 5943",
    scope: "Food · Beverages · Food Additives",
    validity: "1 year",
    recognised: "Regional Arab markets",
    href: "",
    urlText: "",
    records: "8,000+",
    notes:
      "Egypt's national food safety body has a halal certification unit. Egypt is a major halal food consumer market with 100M+ Muslim population. JAKIM and IFANCA certs accepted for import. Egypt's Al-Azhar University plays advisory role in halal standards.",
  },
  {
    num: 16,
    name: "HFA",
    fullName: "Halal Food Authority",
    country: "United Kingdom",
    region: "Europe",
    type: "NGO / Private",
    est: "1994",
    standard: "HFA Halal Standard (proprietary); aligned with OIC/SMIIC 1",
    scope:
      "Meat & Poultry · Food Processing · Food Services · Ingredients · Beverages",
    validity: "1 year",
    recognised:
      "Malaysia (JAKIM — on approved list) · UAE (ESMA) · Saudi Arabia · GCC countries — strong international acceptance",
    href: "https://www.halalfoodauthority.com/check",
    urlText: "www.halalfoodauthority.com/check",
    records: "19,000+",
    notes:
      "One of UK's oldest and most internationally recognised halal certification bodies. On JAKIM's and ESMA's approved body lists. Approves mechanical slaughter (accepted by most Gulf markets). 2,000+ certified companies. Key certifier for British food exports to Middle East.",
  },
  {
    num: 17,
    name: "HMC",
    fullName: "Halal Monitoring Committee",
    country: "United Kingdom",
    region: "Europe",
    type: "NGO / Religious",
    est: "2000",
    standard: "HMC Halal Certification Standard",
    scope: "Meat & Poultry · Food Services · Restaurants · Food Retail",
    validity: "1 year",
    recognised:
      "UK domestic market primarily; some Gulf acceptance; highly trusted within UK Muslim community",
    href: "https://www.halalhmc.org/certified-businesses",
    urlText: "www.halalhmc.org/certified-businesses",
    records: "8,000+",
    notes:
      "Mandates hand slaughter only — no electrical stunning. Very highly regarded within UK Muslim community for strict standards. Strong focus on slaughter monitoring and supply chain integrity. Less internationally recognised than HFA for export purposes.",
  },
  {
    num: 18,
    name: "GIMDES",
    fullName:
      "Gıda ve İhtiyaç Maddeleri Denetleme ve Sertifikasyon Araştırmaları Der",
    country: "Turkey",
    region: "Europe",
    type: "NGO",
    est: "2005",
    standard: "GIMDES Halal Standard; OIC/SMIIC 1:2019 aligned",
    scope:
      "Food · Beverages · Cosmetics · Pharmaceuticals · Feed · Cleaning Products · Food Additives",
    validity: "1 year",
    recognised:
      "Malaysia (JAKIM — approved list) · UAE (ESMA) · Saudi Arabia · GCC markets — strong international standing",
    href: "https://www.gimdes.org/halal-sertifika-sorgulama",
    urlText: "www.gimdes.org/halal-sertifika-sorgulama",
    records: "15,000+",
    notes:
      "Most internationally recognised Turkish halal certifier. On JAKIM's and ESMA's approved body lists. Certifies companies in Turkey and internationally. Active across European, Turkish, and Gulf markets. Strict standards, widely respected.",
  },
  {
    num: 19,
    name: "TSE Halal",
    fullName:
      "Türk Standardları Enstitüsü — Helal Belgesi (Turkish Standards Institu…)",
    country: "Turkey",
    region: "Europe",
    type: "Government",
    est: "2011",
    standard:
      "TS OIC/SMIIC 1:2019 (Turkish adoption of international halal standard); TS OIC/SMIIC 3 (cosmetics)",
    scope:
      "Food · Beverages · Cosmetics · Pharmaceuticals · Cleaning Products · Tourism & Hospitality",
    validity: "1 year",
    recognised:
      "OIC countries (government body adds credibility); growing international acceptance",
    href: "",
    urlText: "",
    records: "10,000+",
    notes:
      "Government-backed Turkish halal certification. Aligned with OIC/SMIIC international standards. Increasingly important as Turkey positions itself as global halal hub. TSE also covers halal tourism certification under OIC/SMIIC 24.",
  },
  {
    num: 20,
    name: "CDIAL",
    fullName:
      "Centre de Documentation et d'Information de l'Assurance de la Licéité",
    country: "France",
    region: "Europe",
    type: "Religious / NGO",
    est: "1995",
    standard: "CDIAL Halal Standard",
    scope: "Food · Meat & Poultry · Food Processing · Cosmetics",
    validity: "1 year",
    recognised:
      "Some Middle East and North Africa markets; primarily France domestic",
    href: "",
    urlText: "",
    records: "6,000+",
    notes:
      "One of three major halal certifiers in France alongside AVS and Mosquée de Lyon. Linked to Grande Mosquée de Paris. France has a large Muslim population (~5.7M) and is a significant halal food market and producer.",
  },
  {
    num: 21,
    name: "Halal Control",
    fullName: "Halal Control e.K.",
    country: "Germany",
    region: "Europe",
    type: "Commercial (ISO 17065 Accredited)",
    est: "1998",
    standard: "OIC/SMIIC 1:2019; ISO/TS 16000 aligned; ELZAS alignment",
    scope:
      "Food · Beverages · Food Ingredients · Cosmetics · Pharmaceuticals · Feed · Food Additives · Flavours · Enzymes",
    validity: "1 year",
    recognised:
      "Malaysia (JAKIM — approved list) · UAE (ESMA approved) · Saudi Arabia · GCC — strong international standing",
    href: "https://www.halal-control.de/halal-check",
    urlText: "www.halal-control.de/halal-check",
    records: "12,000+",
    notes:
      "One of Europe's most internationally recognised halal certification bodies. ISO 17065 accredited. On JAKIM's and ESMA's approved lists. Particularly strong in food ingredient and additive certification. Certifies food ingredients for major European food manufacturers exporting globally.",
  },
  {
    num: 22,
    name: "IFRC Belgium",
    fullName: "Institut Français de Certification Halal — Brussels",
    country: "Belgium",
    region: "Europe",
    type: "NGO",
    est: "2007",
    standard: "Aligned with OIC/SMIIC 1; Belgian Islamic certification protocol",
    scope: "Food · Meat & Poultry · Beverages",
    validity: "1 year",
    recognised: "Gulf markets; Belgium/EU domestic",
    href: "",
    urlText: "",
    records: "3,000+",
    notes:
      "Belgium is a major transit and re-export hub for halal products. Belgian Muslim community (~700K) is significant domestic market. Several Belgian certifiers operate under EU Halal framework.",
  },
  {
    num: 23,
    name: "HCI",
    fullName: "Halal Certification Institute Italy",
    country: "Italy",
    region: "Europe",
    type: "NGO",
    est: "2010",
    standard: "Aligned with OIC/SMIIC 1; Italian Halal Standard",
    scope: "Food · Beverages · Cosmetics",
    validity: "1 year",
    recognised: "UAE; selected OIC markets",
    href: "",
    urlText: "",
    records: "2,000+",
    notes:
      "Italy's food manufacturing sector is significant for halal export potential. Growing Italian Muslim community. Italian halal certification infrastructure still developing.",
  },
  {
    num: 24,
    name: "SANHA",
    fullName: "South African National Halaal Authority",
    country: "South Africa",
    region: "Africa",
    type: "NGO / Religious",
    est: "1994",
    standard: "SANHA Halaal Certification Standard (SANS 1841 aligned)",
    scope:
      "Food · Meat & Poultry · Food Processing · Food Services · Abattoir · Ingredients · Feed",
    validity: "1 year",
    recognised:
      "Malaysia (JAKIM — approved list) · UAE (ESMA) · Saudi Arabia · OIC countries generally",
    href: "https://www.sanha.org.za/consumer/find-a-product",
    urlText: "www.sanha.org.za/consumer/find-a-product",
    records: "54,000+",
    notes:
      "South Africa's largest and most internationally recognised halal authority. On JAKIM's and ESMA's approved body lists. South Africa is a significant halal beef and food exporter. SANHA particularly strong in meat and poultry certification.",
  },
  {
    num: 25,
    name: "MJC Halaal",
    fullName: "Muslim Judicial Council Halaal Trust",
    country: "South Africa",
    region: "Africa",
    type: "Religious",
    est: "1979",
    standard: "MJC Halaal Standard",
    scope: "Food · Meat & Poultry · Food Services · Abattoir",
    validity: "1 year",
    recognised:
      "UAE; Malaysia (limited); primarily Western Cape domestic",
    href: "",
    urlText: "",
    records: "8,000+",
    notes:
      "One of South Africa's oldest halal certifiers. Primarily serves Western Cape region. Stricter hand-slaughter requirements. Some recognition in Gulf markets alongside SANHA.",
  },
  {
    num: 26,
    name: "NIHT",
    fullName: "National Independent Halaal Trust",
    country: "South Africa",
    region: "Africa",
    type: "NGO",
    est: "1996",
    standard: "NIHT Halaal Standard",
    scope: "Food · Food Processing · Food Services",
    validity: "1 year",
    recognised: "South African domestic market; some Gulf markets",
    href: "",
    urlText: "",
    records: "4,000+",
    notes:
      "Third major halal certifier in South Africa. Less internationally recognised than SANHA but active in domestic food manufacturing. Growing presence.",
  },
  {
    num: 27,
    name: "SUPKEM",
    fullName: "Supreme Council of Kenya Muslims — Halal Certification",
    country: "Kenya",
    region: "Africa",
    type: "Religious / NGO",
    est: "2000",
    standard: "Kenya Bureau of Standards (KEBS) Halal Standard alignment",
    scope: "Food · Meat & Poultry · Food Services",
    validity: "1 year",
    recognised: "East African markets; some OIC countries",
    href: "",
    urlText: "",
    records: "4,000+",
    notes:
      "Primary halal certifier for Kenya's significant halal food production and export sector. Kenya is an important halal food exporter in East Africa, particularly meat and horticulture products to Gulf markets.",
  },
  {
    num: 28,
    name: "IMANOR Halal",
    fullName: "Institut Marocain de Normalisation — Certification Halal",
    country: "Morocco",
    region: "Africa",
    type: "Government",
    est: "2002",
    standard: "NM 08.0.800 (Morocco Halal Standard)",
    scope: "Food · Beverages · Cosmetics",
    validity: "1 year",
    recognised: "Arab and European markets",
    href: "",
    urlText: "",
    records: "5,000+",
    notes:
      "Morocco's national standards body halal programme. Morocco is a significant food exporter to Europe and Arab markets. Moroccan halal industry serves both domestic Muslim majority population and export markets.",
  },
  {
    num: 29,
    name: "IFANCA",
    fullName: "Islamic Food and Nutrition Council of America",
    country: "United States",
    region: "Americas",
    type: "NGO / Religious",
    est: "1982",
    standard: "IFANCA Halal Certification Standard",
    scope:
      "Food · Food Ingredients · Beverages · Pharmaceuticals · Cosmetics · Food Additives · Flavours · Enzymes · Vitamins",
    validity: "1 year",
    recognised:
      "Malaysia (JAKIM — approved list) · UAE (ESMA) · Saudi Arabia · GCC · Indonesia (BPJPH/MUI) · virtually all major OIC import markets",
    href: "https://www.ifanca.org/Pages/halal-directory.aspx",
    urlText: "www.ifanca.org/Pages/halal-directory.aspx",
    records: "88,000+",
    notes:
      "One of the world's oldest (1982) and most globally recognised halal certifiers. Particularly authoritative for food ingredients, additives, flavours, and pharma ingredients. On JAKIM's and ESMA's approved lists. Widely accepted wherever halal certification is required globally.",
  },
  {
    num: 30,
    name: "HFSAA",
    fullName: "Halal Food Standards Alliance of America",
    country: "United States",
    region: "Americas",
    type: "NGO",
    est: "2003",
    standard: "HFSAA Halal Standard",
    scope: "Food · Beverages · Cosmetics · Pharmaceuticals",
    validity: "1 year",
    recognised: "OIC countries; less internationally recognised than IFANCA",
    href: "",
    urlText: "",
    records: "8,000+",
    notes:
      "Alternative US halal certifier. Primarily serves US domestic halal food market. Less globally recognised than IFANCA. Used by smaller manufacturers serving North American Muslim consumer market.",
  },
  {
    num: 31,
    name: "ISNA Halal",
    fullName: "Islamic Society of North America — Halal Certification Program",
    country: "Canada",
    region: "Americas",
    type: "Religious / NGO",
    est: "1982",
    standard: "ISNA Halal Standard; ISNA Canada Halal Standard",
    scope: "Food · Meat & Poultry · Dairy · Beverages · Food Additives",
    validity: "1 year",
    recognised: "Canada domestic; UAE; some OIC markets",
    href: "https://www.isnahalal.ca/verify",
    urlText: "www.isnahalal.ca/verify",
    records: "12,000+",
    notes:
      "Primary halal certification body for Canada. ISNA Halal logo widely recognised in Canadian Muslim community. Canada is a significant halal food producer and exporter (beef, lamb, grain, seafood). Some OIC market acceptance.",
  },
  {
    num: 32,
    name: "CIBAL Halal",
    fullName:
      "Centro Islâmico Beneficente de Assistência e Letramento — Halal",
    country: "Brazil",
    region: "Americas",
    type: "Religious / NGO",
    est: "2001",
    standard: "CIBAL Halal Standard; OIC/SMIIC 1 aligned",
    scope: "Meat & Poultry · Dairy · Processed Foods · Food Ingredients",
    validity: "1 year",
    recognised:
      "Malaysia (JAKIM — approved list) · UAE · Saudi Arabia · Egypt · GCC — critical for Brazilian halal beef export",
    href: "",
    urlText: "",
    records: "18,000+",
    notes:
      "Brazil is the world's largest halal beef exporter, shipping to GCC, Malaysia, Egypt, and 100+ markets. CIBAL Halal is on JAKIM's approved list. Brazil's halal industry is one of the world's most important, especially for meat. CIBAL certifies major Brazilian meatpackers JBS, BRF, and Marfrig.",
  },
  {
    num: 33,
    name: "Fambras Halal",
    fullName:
      "Federação das Associações Muçulmanas do Brasil — Halal (Federation of …)",
    country: "Brazil",
    region: "Americas",
    type: "Religious / NGO",
    est: "1988",
    standard: "Fambras Halal Standard (OIC/SMIIC 1 aligned)",
    scope: "Meat & Poultry · Food · Dairy · Processed Foods",
    validity: "1 year",
    recognised:
      "UAE · Saudi Arabia · Malaysia (JAKIM) · Jordan · Egypt",
    href: "",
    urlText: "",
    records: "14,000+",
    notes:
      "Second major Brazilian halal certifier alongside CIBAL Halal. Both CIBAL and Fambras certify Brazil's massive halal meat export industry. Brazil exports over USD 5 billion in halal food annually. Essential for supply chain to OIC markets.",
  },
  {
    num: 34,
    name: "Halal Argentina",
    fullName: "Centro Islámico de la República Argentina — Halal",
    country: "Argentina",
    region: "Americas",
    type: "Religious / NGO",
    est: "1996",
    standard:
      "Argentinian Halal Standard; aligned with international requirements",
    scope: "Meat & Poultry · Food · Dairy",
    validity: "1 year",
    recognised: "Gulf markets; Argentina is a major halal beef exporter",
    href: "",
    urlText: "",
    records: "5,000+",
    notes:
      "Argentina is a significant halal meat exporter to Gulf and OIC markets. Argentine halal beef and lamb are exported mainly to Saudi Arabia, UAE, Turkey, and Egypt. Argentine Islamic bodies certify major meatpacking facilities.",
  },
  {
    num: 35,
    name: "AFIC",
    fullName: "Australian Federation of Islamic Councils — Halal Division",
    country: "Australia",
    region: "Oceania",
    type: "Religious / NGO",
    est: "1964",
    standard: "AFIC Halal Standard",
    scope:
      "Food · Meat & Poultry · Dairy · Seafood · Food Processing · Ingredients",
    validity: "1 year",
    recognised:
      "Malaysia (JAKIM — approved list) · UAE · Saudi Arabia · OIC countries — Australia is a top halal food exporter",
    href: "",
    urlText: "",
    records: "22,000+",
    notes:
      "Australia's oldest and most internationally recognised halal body. On JAKIM's and ESMA's approved lists. Australia exports significant volumes of halal beef, lamb, mutton, and seafood to GCC, SE Asia, and other OIC markets. Several competing Australian bodies including HCA and ICCV.",
  },
  {
    num: 36,
    name: "HCA Australia",
    fullName: "Halal Certification Authority Australia",
    country: "Australia",
    region: "Oceania",
    type: "Commercial (Accredited)",
    est: "2000",
    standard: "HCA Halal Standard; ESMA and JAKIM aligned",
    scope:
      "Food · Meat & Poultry · Dairy · Seafood · Food Processing · Food Services",
    validity: "1 year",
    recognised:
      "UAE (ESMA) · Malaysia (JAKIM) · Saudi Arabia · OIC markets",
    href: "https://www.hca.org.au/verify",
    urlText: "www.hca.org.au/verify",
    records: "14,000+",
    notes:
      "One of Australia's major halal certifiers, competing with AFIC. On JAKIM's and ESMA's approved lists. Certifies meat processors and food manufacturers across Australia and New Zealand. Strong presence in Australian halal meat export industry.",
  },
  {
    num: 37,
    name: "FIANZ",
    fullName: "Federation of Islamic Associations of New Zealand",
    country: "New Zealand",
    region: "Oceania",
    type: "Religious / NGO",
    est: "1979",
    standard: "FIANZ Halal Standard",
    scope: "Meat & Poultry · Dairy · Seafood · Food Processing",
    validity: "1 year",
    recognised:
      "Malaysia (JAKIM — approved list) · UAE · Saudi Arabia · GCC countries",
    href: "",
    urlText: "",
    records: "9,000+",
    notes:
      "New Zealand's primary halal certifier. NZ exports significant volumes of halal lamb, mutton, beef, and dairy to Middle East and SE Asia. On JAKIM's approved list. New Zealand's halal industry is substantial relative to population — major supplier to Gulf markets.",
  },
  {
    num: 38,
    name: "KMF",
    fullName: "Korea Muslim Federation — Halal Certification",
    country: "South Korea",
    region: "East Asia",
    type: "Religious / NGO",
    est: "1967",
    standard: "KMF Halal Standard; JAKIM-accepted",
    scope:
      "Food · Beverages · Cosmetics · Pharmaceuticals · Food Ingredients",
    validity: "1 year",
    recognised:
      "Malaysia (JAKIM — approved) · UAE · Saudi Arabia · OIC markets",
    href: "",
    urlText: "",
    records: "8,000+",
    notes:
      "Primary halal certification body for South Korea. On JAKIM's approved list. South Korea is significant in food exports and K-beauty cosmetics. Korean halal food exports growing rapidly particularly in SE Asian and Middle East markets. Samsung, LG Food divisions seek KMF certs for export.",
  },
  {
    num: 39,
    name: "JHA",
    fullName: "Japan Halal Association",
    country: "Japan",
    region: "East Asia",
    type: "NGO",
    est: "2008",
    standard: "JHA Halal Standard; aligned with OIC/SMIIC",
    scope: "Food · Beverages · Food Ingredients · Cosmetics",
    validity: "1 year",
    recognised:
      "Malaysia (partial recognition); UAE; OIC markets (growing)",
    href: "",
    urlText: "",
    records: "4,000+",
    notes:
      "Japan's halal certification infrastructure is growing rapidly to serve Muslim tourists and export markets. Multiple competing Japanese halal bodies. Japan's major food manufacturers seeking halal certs for SE Asian and Middle East export. Japanese food exports to OIC markets are significant.",
  },
  {
    num: 40,
    name: "OIC/SMIIC",
    fullName: "Standards and Metrology Institute for Islamic Countries",
    country: "International (HQ: Istanbul, Turkey)",
    region: "International",
    type: "Intergovernmental Standards Body",
    est: "2010",
    standard:
      "OIC/SMIIC 1:2019 (Halal Food — General Guidelines); OIC/SMIIC 2:2019 (Pharmaceuticals); OIC/SMIIC 3:2021 (Cosmetics); OIC/SMIIC 24:2019 (Halal Tourism & Hospitality)",
    scope:
      "Standards body covering all categories: Food · Pharmaceuticals · Cosmetics · Tourism",
    validity: "N/A — standards body, does not certify",
    recognised: "All 57 OIC member states",
    href: "",
    urlText: "",
    records: "N/A",
    notes:
      "OIC/SMIIC develops and publishes international halal standards adopted by OIC member countries. NOT a certification body — issues standards documents, not certificates. OIC/SMIIC 1:2019 is the foundational international halal standard. National bodies like JAKIM, TSE, and BPJPH align their standards with OIC/SMIIC documents.",
  },
  {
    num: 41,
    name: "World Halal Council",
    fullName: "World Halal Council",
    country: "International (Secretariat: Jakarta, Indonesia)",
    region: "International",
    type: "International Coordination Body",
    est: "1999",
    standard: "Member bodies' own standards — WHC facilitates mutual recognition",
    scope: "Network — all categories via member certification bodies",
    validity: "N/A — coordination body",
    recognised: "Member countries via their national certifiers",
    href: "",
    urlText: "",
    records: "N/A",
    notes:
      "Coordination body for halal certification bodies globally. Members include JAKIM, MUI, MUIS, IFANCA, and 40+ bodies. WHC facilitates mutual recognition agreements between member certifiers. Does not issue certificates.",
  },
]
