from django.template.defaulttags import register


@register.filter(name='dict_value')
def dict_value(dict, key):
    return dict[key]


@register.filter(name='delete')
def delete(dataset):
    return dataset[8:]


@register.filter(name='delete_pre')
def delete_pre(dataset):
    return dataset[11:]