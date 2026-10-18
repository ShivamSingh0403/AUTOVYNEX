from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib import messages
from .models import VehicleMake, VehicleModel, VehicleVariant


def vehicle_selector_page(request):
    makes = VehicleMake.objects.all().order_by('name')
    selected_variant = None
    selected_variant_id = request.session.get('selected_variant_id')
    if selected_variant_id:
        try:
            selected_variant = VehicleVariant.objects.select_related('model__make').get(pk=selected_variant_id)
        except VehicleVariant.DoesNotExist:
            pass

    return render(request, 'vehicles/selector.html', {
        'makes': makes,
        'selected_variant': selected_variant
    })


def api_models_by_make(request):
    make_id = request.GET.get('make_id')
    if not make_id:
        return JsonResponse({'models': []})
    
    models = VehicleModel.objects.filter(make_id=make_id).order_by('name')
    data = [{'id': m.id, 'name': m.name, 'body_type': m.body_type} for m in models]
    return JsonResponse({'models': data})


def api_variants_by_model(request):
    model_id = request.GET.get('model_id')
    if not model_id:
        return JsonResponse({'variants': []})

    variants = VehicleVariant.objects.filter(model_id=model_id).order_by('-year_to', 'name')
    data = [{
        'id': v.id,
        'name': v.name,
        'fuel_type': v.fuel_type,
        'transmission': v.transmission,
        'year_from': v.year_from,
        'year_to': v.year_to,
        'engine_cc': v.engine_cc,
        'power_hp': v.power_hp
    } for v in variants]
    return JsonResponse({'variants': data})


def select_vehicle_session(request):
    if request.method == 'POST':
        variant_id = request.POST.get('variant_id')
        if variant_id:
            try:
                variant = VehicleVariant.objects.select_related('model__make').get(pk=variant_id)
                request.session['selected_variant_id'] = variant.id
                messages.success(request, f"Active Vehicle set to: {variant.display_name}. Compatible spare parts will be highlighted!")
            except VehicleVariant.DoesNotExist:
                messages.error(request, "Selected vehicle variant was not found.")
    
    return redirect(request.META.get('HTTP_REFERER', 'inventory:shop'))


def clear_vehicle_session(request):
    if 'selected_variant_id' in request.session:
        del request.session['selected_variant_id']
        messages.info(request, "Active vehicle filter cleared. Now showing all parts.")
    return redirect(request.META.get('HTTP_REFERER', 'core:home'))
