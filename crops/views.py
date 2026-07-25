from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from .models import Crop
from .forms import CropForm
from farms.models import Farm

@login_required
def crop_list(request):
    farms = Farm.objects.filter(owner=request.user)  # Changed: user -> owner
    crops = Crop.objects.filter(farm__in=farms).select_related('farm')
    
    # Optional: Add filtering
    status_filter = request.GET.get('status')
    if status_filter:
        crops = crops.filter(status=status_filter)
    
    return render(request, 'crops/crop_list.html', {
        'crops': crops,
        'status_filter': status_filter,
    })

@login_required
def crop_create(request):
    # Check if user has any farms
    if not Farm.objects.filter(owner=request.user).exists():  # Changed: user -> owner
        messages.warning(request, 'Please create a farm first before adding crops.')
        return redirect('farms:farm_list')
    
    if request.method == 'POST':
        form = CropForm(request.POST, user=request.user)
        if form.is_valid():
            crop = form.save()
            messages.success(request, f'✅ Crop "{crop.name}" created successfully!')
            return redirect('crops:crop_list')
    else:
        form = CropForm(user=request.user)
    
    return render(request, 'crops/crop_form.html', {
        'form': form,
        'title': 'Add New Crop',
        'submit_text': 'Create Crop'
    })

@login_required
def crop_edit(request, pk):
    crop = get_object_or_404(Crop, pk=pk, farm__owner=request.user)  # Changed: farm__user -> farm__owner
    
    if request.method == 'POST':
        form = CropForm(request.POST, instance=crop, user=request.user)
        if form.is_valid():
            crop = form.save()
            messages.success(request, f'✅ Crop "{crop.name}" updated successfully!')
            return redirect('crops:crop_list')
    else:
        form = CropForm(instance=crop, user=request.user)
    
    return render(request, 'crops/crop_form.html', {
        'form': form,
        'title': 'Edit Crop',
        'submit_text': 'Update Crop',
        'crop': crop
    })

@login_required
def crop_delete(request, pk):
    crop = get_object_or_404(Crop, pk=pk, farm__owner=request.user)  # Changed: farm__user -> farm__owner
    
    if request.method == 'POST':
        crop_name = crop.name
        crop.delete()
        messages.success(request, f'🗑️ Crop "{crop_name}" deleted successfully!')
        return redirect('crops:crop_list')
    
    return render(request, 'crops/crop_confirm_delete.html', {'crop': crop})

@login_required
def crop_detail(request, pk):
    crop = get_object_or_404(Crop, pk=pk, farm__owner=request.user)  # Changed: farm__user -> farm__owner
    return render(request, 'crops/crop_detail.html', {'crop': crop})