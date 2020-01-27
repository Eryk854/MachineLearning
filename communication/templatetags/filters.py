from django.template.defaulttags import register


@register.filter(name='dict_value')
def dict_value(dict, key):
    return dict[key]

@register.filter(name='delete')
def delete(dataset):
    return dataset[8:]