// Variable global para almacenar datos del formulario
let formData = {};

function deleteTabs() {
    XTABS = TABS;
    for (let i = 0; i < XTABS.length; i++) {
        if (XTABS[i].conditions && !isTabAvailable(i)) {
            console.log('Borrando tab:', XTABS[i].id);
            XTABS.splice(i, 1);
            document.getElementById("tab-"+i)?.remove();
        }
    }
    TABS = XTABS;
}

function getRealTabIndex(targetDisplayIndex) {
    let realIndex = -1;
    let displayCount = -1;
    
    for (let i = 0; i < TABS.length; i++) {
        if (!TABS[i].conditions || isTabAvailable(i)) {
            displayCount++;
            if (displayCount === targetDisplayIndex) {
                realIndex = i;
                break;
            }
        }
    }
    
    return realIndex;
}

function getCurrentRealTabIndex() {
    const currentTabId = document.querySelector('.tab-panel:not(.hidden)').id.replace('tab-', '');
    return TABS.findIndex(tab => tab.id === currentTabId);
}

async function changeTab(targetTabIndex) {
    // Verificar que el índice esté dentro de los límites
    if (targetTabIndex < 0 || targetTabIndex >= TABS.length) {
        console.error(`Índice de tab inválido: ${targetTabIndex}`);
        return;
    }

    // Verificar si el tab está disponible
    if (!isTabAvailable(targetTabIndex)) {
        console.log(`Tab ${targetTabIndex} no está disponible`);
        return;
    }

    const currentTabIndex = parseInt(document.querySelector('input[name="current_tab"]').value);
    const tabs = document.querySelectorAll('.tab-panel');
    
    // Verificar que existan los tabs
    if (!tabs || tabs.length === 0) {
        console.error('No se encontraron tabs en el DOM');
        return;
    }

    // Verificar que los índices sean válidos
    if (currentTabIndex < 0 || currentTabIndex >= tabs.length || 
        targetTabIndex < 0 || targetTabIndex >= tabs.length) {
        console.error('Índices de tabs fuera de rango');
        return;
    }

    const currentTab = tabs[currentTabIndex];
    const newTab = tabs[targetTabIndex];
    
    // Verificar que los elementos existan
    if (!currentTab || !newTab) {
        console.error('No se encontró el tab actual o el nuevo tab');
        return;
    }

    try {
        // Obtener configuraciones de transición
        const currentTransition = TABS[currentTabIndex]?.transition || { enter: 'fade', exit: 'fade' };
        const newTransition = TABS[targetTabIndex]?.transition || { enter: 'fade', exit: 'fade' };
        
        // Aplicar transiciones
        if (currentTransition.exit !== 'none') {
            currentTab.classList.add(`${currentTransition.exit}-exit`);
        }
        
        if (newTransition.enter !== 'none') {
            newTab.classList.add(`${newTransition.enter}-enter`);
        }
        
        await new Promise(resolve => setTimeout(resolve, 500));
        
        // Limpiar clases
        currentTab.classList.remove('active', 'slide-down-exit', 'slide-up-exit', 'fade-exit');
        newTab.classList.remove('slide-down-enter', 'slide-up-enter', 'fade-enter');
        
        // Activar nueva pestaña
        newTab.classList.add('active');
        
        // Actualizar UI
        updateProgressBar(targetTabIndex);
        document.querySelector('input[name="current_tab"]').value = targetTabIndex;
        focusFirstInput(newTab);
        centerActiveProgressStep();
    } catch (error) {
        console.error('Error al cambiar de tab:', error);
    }
}

// Función para verificar disponibilidad de tab
function isTabAvailable(tabIndex) {
    const tabConfig = TABS[tabIndex];
    if (!tabConfig?.conditions) return true;
    
    return tabConfig.conditions.every(condition => {
        const [tabId, fieldName] = condition.field.split('.');
        const fieldValue = formData[fieldName];

        switch (condition.operator) {
            case '==':
                return fieldValue == condition.value;
            case '!=':
                return fieldValue != condition.value;
            case '>':
                return parseFloat(fieldValue) > parseFloat(condition.value);
            case '<':
                return parseFloat(fieldValue) < parseFloat(condition.value);

            case 'includes': {
                const values = condition.value.split('|').map(v => v.trim().toLowerCase());
                return values.some(v => fieldValue.toLowerCase().includes(v));
            }

            case '!includes': {
                const values = condition.value.split('|').map(v => v.trim().toLowerCase());
                return values.every(v => !fieldValue.toLowerCase().includes(v));
            }

            default:
                return fieldValue === condition.value;
        }
    });
}

// Función para validar y avanzar
async function validateAndNext(currentTabIndex) {
    if (await validateTab(currentTabIndex)) {
        updateFormData();
        
        let nextTabIndex = currentTabIndex + 1;
        
        // Buscar siguiente tab disponible
        while (nextTabIndex < TABS.length && !isTabAvailable(nextTabIndex)) {
            nextTabIndex++;
        }
        
        if (nextTabIndex < TABS.length) {
            await changeTab(nextTabIndex);
        } else {
            // Si no hay más tabs disponibles hacia adelante, verificar si podemos retroceder
            let prevTabIndex = currentTabIndex - 1;
            while (prevTabIndex >= 0 && !isTabAvailable(prevTabIndex)) {
                prevTabIndex--;
            }
            
            if (prevTabIndex >= 0) {
                await changeTab(prevTabIndex);
            } else {
                // Si no hay tabs disponibles en ninguna dirección, enviar formulario
                document.getElementById('multiTabForm').submit();
            }
        }
    }
}

async function goToPreviousTab() {
    const currentTabIndex = parseInt(document.querySelector('input[name="current_tab"]').value);
    let prevTabIndex = currentTabIndex - 1;
    
    // Buscar el tab anterior disponible
    while (prevTabIndex >= 0) {
        if (isTabAvailable(prevTabIndex)) {
            await changeTab(prevTabIndex);
            return;
        }
        prevTabIndex--;
    }
    
    console.log('No hay secciones anteriores disponibles');
}

// Función de validación completa
async function validateTab(tabIndex) {
    const currentTab = document.querySelectorAll('.tab-panel')[tabIndex];
    const inputs = currentTab.querySelectorAll('input, textarea, select');
    let isValid = true;
    let firstInvalidField = null;

    // Eliminar mensajes de error previos
    document.querySelectorAll('.error-message').forEach(el => el.remove());

    inputs.forEach(field => {
        field.style.borderColor = '';
        field.classList.remove('error');
        //console.log(field.type, field.name, field.required);
        // Validación por tipo de campo
        if (field.required) {
            let errorMessage = 'Este campo es obligatorio';
            let isInvalid = false;
            switch(field.type) {
                case 'radio-group':
                case 'radio':
                    const radios = document.querySelectorAll(`input[name="${field.name}"]`);
                    //console.log(radios);
                    const algunoSeleccionado = Array.from(radios).some(radio => radio.checked);
                    //console.log(algunoSeleccionado)
                    if (!algunoSeleccionado) {
                        isInvalid=true;
                    }
                    break;
                case 'checkbox':
                    isInvalid = !field.checked;
                    break;
                case 'date':
                case 'time':
                case 'datetime-local':
                    isInvalid = !field.value;
                    errorMessage = `Seleccione una ${field.type === 'date' ? 'fecha' : field.type === 'time' ? 'hora' : 'fecha y hora'}`;
                    break;
                default:
                    isInvalid = !field.value.trim();
            }

            if (isInvalid) {
                markFieldAsInvalid(field, errorMessage);
                if (!firstInvalidField) firstInvalidField = field;
                isValid = false;
                return;
            }
        }

        // Validaciones específicas
        if (['date', 'datetime-local'].includes(field.type) && field.value) {
            const dateValue = new Date(field.value);
            if (field.min && new Date(field.min) > dateValue) {
                markFieldAsInvalid(field, `La fecha mínima es ${formatDate(new Date(field.min))}`);
                isValid = false;
                return;
            }
            if (field.max && new Date(field.max) < dateValue) {
                markFieldAsInvalid(field, `La fecha máxima es ${formatDate(new Date(field.max))}`);
                isValid = false;
                return;
            }
        }

        if (field.type === 'time' && field.value) {
            if (field.min && field.value < field.min) {
                markFieldAsInvalid(field, `La hora mínima es ${field.min}`);
                isValid = false;
                return;
            }
            if (field.max && field.value > field.max) {
                markFieldAsInvalid(field, `La hora máxima es ${field.max}`);
                isValid = false;
                return;
            }
        }

        if ((field.type === 'number' || field.type === 'range') && field.value) {
            const numValue = parseFloat(field.value);
            if (field.min && numValue < parseFloat(field.min)) {
                markFieldAsInvalid(field, `El valor mínimo es ${field.min}`);
                isValid = false;
                return;
            }
            if (field.max && numValue > parseFloat(field.max)) {
                markFieldAsInvalid(field, `El valor máximo es ${field.max}`);
                isValid = false;
                return;
            }
        }

        if (field.pattern && field.value && !new RegExp(field.pattern).test(field.value)) {
            markFieldAsInvalid(field, field.title || 'Formato inválido');
            isValid = false;
            return;
        }

        if (field.minLength >= 0 && field.value.length < field.minLength) {
            markFieldAsInvalid(field, `Mínimo ${field.minLength} caracteres`);
            isValid = false;
            return;
        }

        if (field.maxLength >= 0 && field.value.length > field.maxLength) {
            markFieldAsInvalid(field, `Máximo ${field.maxLength} caracteres`);
            isValid = false;
            return;
        }

        if (field.type === 'email' && field.value && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(field.value)) {
            markFieldAsInvalid(field, 'Email inválido');
            isValid = false;
            return;
        }
        if (field.type === 'select-multiple') {
            const min = parseInt(field.getAttribute('data-min')) || 0;
            const max = parseInt(field.getAttribute('data-max')) || Infinity;
            const selectedCount = Array.from(field.options).filter(option => option.selected).length;
            if (selectedCount < min || selectedCount > max) {
                if (min!==max) {
                    markFieldAsInvalid(field, `Seleccione entre ${min} y ${max} opciones`);
                } else {
                    markFieldAsInvalid(field, `Seleccione ${max} opciones`);
                }
                isValid = false;
                return;
            }
        }
    });

    // Validar grids
    document.querySelectorAll('.form-grid-container').forEach(container => {
        const required = container.dataset.required === 'true';
        const rows = container.querySelectorAll('tbody tr');
        
        if (required && rows.length === 0) {
            isValid = false;
            const errorMsg = document.createElement('div');
            errorMsg.className = 'error-message';
            errorMsg.textContent = 'Debe agregar al menos un registro';
            container.parentNode.insertBefore(errorMsg, container.nextSibling);
        }
        
        // Validar cada fila
        rows.forEach(row => {
            const inputs = row.querySelectorAll('input, select');
            inputs.forEach(input => {
                if (input.required && !input.value.trim()) {
                    isValid = false;
                    input.style.borderColor = '#f44336';
                }
            });
        });
    });

    if (!isValid && firstInvalidField) {
        showErrorToast('Complete los campos requeridos');
        firstInvalidField.scrollIntoView({ behavior: 'smooth', block: 'center' });
        firstInvalidField.focus();
    }
    
    return isValid;
}

// Funciones auxiliares
function updateFormData() {
    document.querySelectorAll('input, select, textarea').forEach(field => {
        if (field.type === 'checkbox') {
            formData[field.name] = field.checked;
        } else if (field.type === 'radio' && field.checked) {
            formData[field.name] = field.value;
        } else if (field.type !== 'radio') {
            formData[field.name] = field.value;
        }
    });
}

function markFieldAsInvalid(field, message) {
    field.style.borderColor = '#f44336';
    field.classList.add('error');
    
    const errorElement = document.createElement('div');
    errorElement.className = 'error-message';
    errorElement.textContent = message;
    //field.parentNode.insertBefore(errorElement, field.nextSibling);
    $('<div class="error">'+message+'</div>').appendTo($(field).closest('.form-group'));
}

function showErrorToast(message) {
    const toast = document.createElement('div');
    toast.className = 'error-toast';
    toast.textContent = message;
    document.body.appendChild(toast);
    
    setTimeout(() => toast.classList.add('show'), 100);
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => document.body.removeChild(toast), 300);
    }, 5000);
}

function focusFirstInput(tabElement) {
    const focusable = tabElement.querySelector(
        'input:not([type="hidden"]):not([disabled]), textarea:not([disabled]), select:not([disabled])'
    );
    if (focusable) {
        focusable.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        focusable.focus();
    }
}

function updateProgressBar(currentTabIndex) {
    const progressContainer = document.querySelector('.progress-steps-container');
    
    // Limpiar el contenedor
    progressContainer.innerHTML = '';
    cc = 0;
    // Reconstruir el progress bar con solo los tabs disponibles
    TABS.forEach((tab, index) => {
        if (!tab.conditions || isTabAvailable(index)) {
            const step = document.createElement('div');
            step.className = `progress-step ${index === currentTabIndex ? 'active' : ''}`;
            step.dataset.tabId = tab.id;
            cc++;
            step.innerHTML = `
                <span class="step-number">${cc}</span>
                <span class="step-title">${tab.title}</span>
            `;
            
            // Permitir click solo en tabs disponibles
            step.addEventListener('click', () => {
                if (index !== currentTabIndex) {
                    changeTab(index);
                }
            });
            
            progressContainer.appendChild(step);
        }
    });
    
    // Ajustar el layout después de actualizar
    adjustProgressBarLayout();
}

function adjustProgressBarLayout() {
    const progressBar = document.querySelector('.progress-bar');
    const progressContainer = document.querySelector('.progress-steps-container');
    const steps = document.querySelectorAll('.progress-step');
    
    if (steps.length === 0) return;
    
    // Calcular el ancho necesario
    const totalWidth = Array.from(steps).reduce((total, step) => {
        return total + step.offsetWidth;
    }, 0);
    
    // Ajustar el espaciado
    const containerWidth = progressBar.offsetWidth;
    if (totalWidth < containerWidth) {
        const spacing = (containerWidth - totalWidth) / (steps.length + 1);
        progressContainer.style.gap = `${spacing}px`;
        progressContainer.style.justifyContent = 'space-evenly';
    } else {
        progressContainer.style.gap = '15px';
        progressContainer.style.justifyContent = 'flex-start';
    }
}

function centerActiveProgressStep() {
    if (window.innerWidth < 768 || 1) {
        const progressBar = document.querySelector('.progress-bar');
        const activeStep = document.querySelector('.progress-step.active');
        
        if (progressBar && activeStep) {
            progressBar.scrollTo({
                left: activeStep.offsetLeft - (progressBar.offsetWidth / 2) + (activeStep.offsetWidth / 2),
                behavior: 'smooth'
            });
        }
    }
}

function formatDate(date) {
    return date.toLocaleDateString('es-ES', { 
        year: 'numeric', 
        month: 'long', 
        day: 'numeric' 
    });
}

// Inicialización
document.addEventListener('DOMContentLoaded', function() {
    try {
        updateFormData();
        
        // Encontrar el primer tab disponible
        let firstAvailableTab = 0;
        while (firstAvailableTab < TABS.length) {
            if (isTabAvailable(firstAvailableTab)) {
                changeTab(firstAvailableTab);
                break;
            }
            firstAvailableTab++;
        }
        
        if (firstAvailableTab >= TABS.length) {
            console.error('No hay tabs disponibles para mostrar');
        }
        /*
        // Configurar listeners
        document.querySelectorAll('input, select, textarea').forEach(field => {
            field.addEventListener('change', function() {
                updateFormData();
                updateTabVisibility();
            });
        });*/
    } catch (error) {
        console.error('Error en la inicialización:', error);
    }
});

function updateTabVisibility() {
    // Actualizar visibilidad de los tabs

    TABS.forEach((tab, index) => {
        const tabElement = document.getElementById(`tab-${index}`);
        if (tabElement) {
            tabElement.style.display = isTabAvailable(index) ? 'flex' : 'none';
        }
    });

    // Actualizar progress bar
    updateProgressBar(getCurrentRealTabIndex());
    
    // Ajustar layout
    adjustProgressBarLayout();
}

// Función para inicializar grids
function initializeGrids() {
    document.querySelectorAll('.form-grid-container').forEach(container => {
        try {
            const fieldName = container.id.replace('grid-', '');
            let gridData = [];
            
            // Verificar si hay un hidden input existente
            const hiddenInput = container.querySelector('input[type="hidden"]');
            const hasInitialData = container.dataset.initialData;
            
            // Priorizar initialData sobre el valor del hidden input
            if (hasInitialData) {
                try {
                    gridData = JSON.parse(container.dataset.initialData);
                    if (!Array.isArray(gridData)) {
                        console.error('Los datos iniciales del grid deben ser un array');
                        gridData = [];
                    }
                } catch (e) {
                    console.error('Error al parsear initialData:', e);
                    gridData = [];
                }
            }
            
            const isEditable = container.dataset.editable === 'true';
            renderGrid(container, gridData, isEditable, fieldName);
            
            // Si no hay initialData pero hay valor en el hidden input
            if (!hasInitialData && hiddenInput && hiddenInput.value) {
                updateGridFromHiddenValue(container, hiddenInput.value);
            }
        } catch (error) {
            console.error('Error al inicializar grid:', error);
        }
    });
}

// Función para renderizar el grid
function renderGrid(container, data, isEditable, fieldName) {
    try {
        // Guardar referencia al campo hidden antes de limpiar
        const hiddenInput = container.querySelector('input[type="hidden"]');
        const initialValue = hiddenInput ? hiddenInput.value : '';
        
        // Crear tabla
        const table = document.createElement('table');
        table.className = 'form-grid';
        table.innerHTML = `
            <thead>
                <tr>
                    <th style="display:none">Código</th>
                    <th>Nombre</th>
                    <th>Apellidos</th>
                    <th>Fecha Nacimiento</th>
                    <th>Sexo</th>
                    ${isEditable ? '<th>Acciones</th>' : ''}
                </tr>
            </thead>
            <tbody></tbody>
        `;

        const tbody = table.querySelector('tbody');
        
        // Renderizar datos
        if (Array.isArray(data)) {
            data.forEach((row, index) => {
                try {
                    addGridRow(tbody, row, index, isEditable && !row.id, fieldName);
                } catch (rowError) {
                    console.error('Error al agregar fila:', rowError);
                }
            });
        }

        // Limpiar contenedor pero preservar el hidden input
        const containerChildren = Array.from(container.children);
        containerChildren.forEach(child => {
            if (child.tagName !== 'INPUT' || child.type !== 'hidden') {
                container.removeChild(child);
            }
        });

        // Agregar elementos al contenedor
        container.appendChild(table);
        
        if (isEditable) {
            const addRowBtn = document.createElement('button');
            addRowBtn.type = 'button';
            addRowBtn.className = 'btn-add-row';
            addRowBtn.textContent = 'Agregar Registro';
            addRowBtn.onclick = () => {
                try {
                    addGridRow(tbody, {}, -1, true, fieldName);
                } catch (error) {
                    console.error('Error al agregar nueva fila:', error);
                }
            };
            container.appendChild(addRowBtn);
        }

        // Restaurar el valor del hidden input si no hay datos iniciales
        if (!data || data.length === 0) {
            updateGridFromHiddenValue(container, initialValue);
        }
        // Configurar los inputs sin name (se agregarán dinámicamente si se necesita editar)
        const inputs = table.querySelectorAll('input, select');
        inputs.forEach(input => {
            if (input.type !== 'hidden') {
                input.removeAttribute('name');
            }
        });
    } catch (error) {
        console.error('Error al renderizar grid:', error);
        container.innerHTML = '<div class="error-message">Error al cargar la tabla de datos</div>';
        
        // Restaurar el hidden input
        if (!container.querySelector('input[type="hidden"]')) {
            const hiddenInput = document.createElement('input');
            hiddenInput.type = 'hidden';
            hiddenInput.name = fieldName;
            container.appendChild(hiddenInput);
        }
    }
}

function updateGridFromHiddenValue(container, hiddenValue) {
    if (!hiddenValue) return;
    
    try {
        const tbody = container.querySelector('tbody');
        if (!tbody) return;
        
        // Parsear el valor del hidden (formato: codigo,nombre,apellidos,fec_nac,sexo\n...)
        const rows = hiddenValue.split('\n')
            .filter(row => row.trim())
            .map(row => {
                const [codigo, nombre, apellidos, fec_nac, sexo] = row.split('\t');
                return { codigo, nombre, apellidos, fec_nac, sexo };
            });
        
        // Limpiar y agregar filas
        tbody.innerHTML = '';
        rows.forEach((row, index) => {
            addGridRow(tbody, row, index, false, container.id.replace('grid-', ''));
        });
        
    } catch (error) {
        console.error('Error al actualizar grid desde hidden value:', error);
    }
}

// Función para agregar una fila al grid
function addGridRow(tbody, rowData, index, isEditable, fieldName) {
    try {
        const rowId = rowData.id || `new-${Date.now()}-${index}`;
        const tr = document.createElement('tr');
        tr.dataset.rowId = rowId;
        // Crear celdas sin names (se manejarán en el hidden)
        tr.innerHTML = `
            <td style="display:none">
                <input type="text" value="${rowData.codigo || ''}" ${isEditable ? '' : 'readonly'}>
            </td>
            <td>
                <input type="text" value="${rowData.nombre || ''}" ${isEditable ? '' : 'readonly'} required>
            </td>
            <td>
                <input type="text" value="${rowData.apellidos || ''}" ${isEditable ? '' : 'readonly'} required>
            </td>
            <td>
                <input type="date" value="${rowData.fec_nac || ''}" ${isEditable ? '' : 'readonly'} required>
            </td>
            <td>
                <select ${isEditable ? '' : 'disabled'} required>
                    <option value="M" ${rowData.sexo === 'M' ? 'selected' : ''}>Masculino</option>
                    <option value="F" ${rowData.sexo === 'F' ? 'selected' : ''}>Femenino</option>
                </select>
            </td>
            ${isEditable ? 
                '<td><button type="button" class="btn-remove-row">Eliminar</button></td>' : 
                '<td></td>'}
        `;
        // Configurar evento de eliminación
        const removeBtn = tr.querySelector('.btn-remove-row');
        if (removeBtn) {
            removeBtn.onclick = () => {
                tr.remove();
                updateGridHiddenField(tbody.closest('.form-grid-container'));
            };
        }

        // Configurar eventos de cambio
        tr.querySelectorAll('input, select').forEach(input => {
            input.addEventListener('change', () => {
                updateGridHiddenField(tbody.closest('.form-grid-container'));
            });
        });

        tbody.appendChild(tr);
    } catch (error) {
        console.error('Error al crear fila:', error);
        throw error;
    }
}

// Función para actualizar el campo hidden con los datos del grid
function updateGridHiddenField(container) {
    try {
        // Asegurarse que existe el hidden input
        let hiddenInput = container.querySelector('input[type="hidden"]');
        if (!hiddenInput) {
            hiddenInput = document.createElement('input');
            hiddenInput.type = 'hidden';
            hiddenInput.name = container.id.replace('grid-', '');
            container.appendChild(hiddenInput);
        }
        
        const rows = container.querySelectorAll('tbody tr');
        const data = Array.from(rows).map(row => {
            const inputs = row.querySelectorAll('td input, td select');
            return {
                codigo: inputs[0]?.value.trim() || '',
                nombre: inputs[1]?.value.trim() || '',
                apellidos: inputs[2]?.value.trim() || '',
                fec_nac: inputs[3]?.value.trim() || '',
                sexo: inputs[4]?.value.trim() || 'M'
            };
        });

        // Convertir a string con validación
        const gridString = data
            .filter(row => row.nombre || row.apellidos) // Filtrar filas vacías
            .map(row => `${row.codigo}\t${row.nombre}\t${row.apellidos}\t${row.fec_nac}\t${row.sexo}`)
            .join('\n');

        hiddenInput.value = gridString;
    } catch (error) {
        console.error('Error al actualizar campo hidden:', error);
    }
}

// Función para limpiar los campos del grid
function cleanGridFieldsBeforeSubmit() {
    document.querySelectorAll('.form-grid-container').forEach(container => {
        // Eliminar todos los inputs/selects de la tabla excepto el hidden
        const inputs = container.querySelectorAll('input[type="text"], input[type="date"], select');
        inputs.forEach(input => {
            // Remover el name para que no se envíe
            input.removeAttribute('name');
            
            // Opcional: Deshabilitar los campos
            input.disabled = true;
        });
        
        // Asegurarse que solo el hidden field tenga el name original
        const hiddenInput = container.querySelector('input[type="hidden"]');
        if (hiddenInput) {
            hiddenInput.name = container.id.replace('grid-', '');
        }
    });
}

// Función opcional para validación final
function validateBeforeSubmit() {
    let isValid = true;
    
    document.querySelectorAll('.form-grid-container').forEach(container => {
        const required = container.dataset.required === 'true';
        const hiddenInput = container.querySelector('input[type="hidden"]');
        
        if (required && (!hiddenInput || !hiddenInput.value.trim())) {
            isValid = false;
            showErrorToast('Debe completar todos los campos requeridos');
            
            // Resaltar el grid requerido
            container.style.border = '1px solid #f44336';
            container.style.borderRadius = '4px';
            container.style.padding = '10px';
        }
    });
    
    return isValid;
}

// Inicializar grids al cargar la página
document.addEventListener('DOMContentLoaded', function() {
// Modificar el event listener del formulario
    document.getElementById('multiTabForm').addEventListener('submit', async function(e) {
        $('#btn-submit').prop('disabled', true);
        currentTabIndex = parseInt(document.querySelector('input[name="current_tab"]').value);
        console.log('currentTabIndex:', currentTabIndex);
        if(! await validateTab(currentTabIndex)) {
            e.preventDefault();
            $('#btn-submit').prop('disabled', false);
            return false;
        } else {
            // Limpiar los campos de la tabla antes de enviar
            cleanGridFieldsBeforeSubmit();
            //$('div.form-grid-container').remove();
            // Opcional: Validación adicional antes de enviar
            if (!validateBeforeSubmit()) {
                e.preventDefault();
                $('#btn-submit').prop('disabled', false);
                return false;
            }
            deleteTabs();
            $('input[type="checkbox"]:not(:checked)').remove();
            $('input[type="checkbox"]:checked').each(function () {
                const name = $(this).attr('name');
                $(`input[type="hidden"][name="${name}"]`).remove();
            });
            return true;
        }
    });
    initializeGrids();
});

// Manejo del resize
window.addEventListener('resize', centerActiveProgressStep);