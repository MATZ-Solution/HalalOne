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