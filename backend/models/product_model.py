# {
#     "canonical_id" : "halal_000001",
#     "norm_name" : "e100 curcurmin (1,7-bis(4-hydroxy-3-methoxyphenyl-1,6-heptadiene-3,5-dione; turmeric yellow; diferuloylmethane; c.i. 75300)",
#     "category_l1" : "Additive",
#     "category_l2" : "Colorant",
#     "halal_status" : "Halal",
#     "sold_in" : [],
#     "marketplace" : [],
#     "companies" : [],
#     "cert_bodies" : ["HFCI India","SANHA South Africa"],
#     "cert_numbers" : [],
#     "cert_expiry" : null,
#     "cert_issue" : null,
#     "source_count" : 2,
#     "health_info" : ["powder or granular. Mushbooh if used as liquid, the solvents has to be Halal. Haraam if hidden ingredient is pork fat based emulsifier in dry mix.","Vegetable extract – orange yellow colour. | has many beneficial health effects, may cause skin irritation, moderately toxic by injection"],
#     "typical_uses" : ["Curry powder","fish fingers","margarine","confectionery","processed cheese","savoury rice"],
#     "source_ids" : ["enumbers_E100","sanha_e100"],
#     "source_files" : ["halal_e_numbers_india","sanha_halal"],
#     "fda_numbers" : [],
#     "barcodes" : [],
#     "company_contact" : []
# }

import os
model = {
  'name': 'halal_products',
  'fields': [
    # Searchable fields (index: true by default)
    {
      "name": "canonical_id",
      "type": "string"
    },
    {
      'name': 'norm_name',
      'type': 'string'
    },
    {
      'name': 'companies',
      'type': 'string[]'
    },
    {
      'name': 'cert_bodies',
      'type': 'string[]'
    },
    {
      'name': 'typical_uses',
      'type': 'string[]'
    },
    {
      'name': 'marketplace',
      'type': 'string[]'
    },
    {
      'name': 'category_l1',
      'type': 'string',
      
    },
    {
      'name': 'category_l2',
      'type': 'string',
      
    },
    {
      'name': 'halal_status',
      'type': 'string',
      
    },
    {
      'name': 'sold_in',
      'type': 'string[]',
      
    },
    {
      'name': 'cert_numbers',
      'type': 'string[]',
      
    },
    {
      'name': 'health_info',
      'type': 'string[]',
      
    },
    {
      'name': 'fda_numbers',
      'type': 'string[]',
      
    },
    {
      'name': 'barcodes',
      'type': 'string[]',
      
    },
    {
      'name': 'embedding',
      'type': "float[]",
      'num_dim': 4096      
    }
  ],
}