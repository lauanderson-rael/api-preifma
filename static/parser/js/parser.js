// --- GLOBALS ---
let currentExamData = null;
let cropper = null;
let currentCroppingId = null;

// --- INIT ---
document.addEventListener('DOMContentLoaded', () => {
  lucide.createIcons();
  setupFileUploads();
});

function setupFileUploads() {
  const examInput = document.getElementById('exam-pdf');
  const keyInput = document.getElementById('key-pdf');
  const btnProcess = document.getElementById('btn-process');
  const zipInput = document.getElementById('zip-upload');

  if (examInput) {
    examInput.onchange = (e) => {
      const file = e.target.files[0];
      if (file) {
        document.getElementById('exam-filename').innerText = file.name;
        document.getElementById('exam-label').classList.add('border-green-400', 'bg-green-50/20');
        btnProcess.disabled = false;
      }
    };
  }

  if (keyInput) {
    keyInput.onchange = (e) => {
      const file = e.target.files[0];
      if (file) {
        document.getElementById('key-filename').innerText = file.name;
        document.getElementById('key-label').classList.add('border-green-400', 'bg-green-50/20');
      }
    };
  }

  if (btnProcess) btnProcess.onclick = startProcessing;
  if (zipInput) zipInput.onchange = handleZipUpload;
}

// --- API CALLS ---
async function startProcessing() {
  const examFile = document.getElementById('exam-pdf').files[0];
  const keyFile = document.getElementById('key-pdf').files[0];
  const apiKey = document.getElementById('api-key')?.value;

  if (!examFile) return;

  showState('processing');
  const formData = new FormData();
  formData.append('exam_pdf', examFile);
  if (keyFile) formData.append('answer_key_pdf', keyFile);
  if (apiKey) formData.append('api_key_override', apiKey);

  try {
    updateProcessingStatus('Iniciando análise...', 10);
    const response = await fetch('/parser/process/', {
      method: 'POST',
      body: formData
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || 'Erro no processamento');
    }

    currentExamData = await response.json();
    loadEditor();
  } catch (err) {
    alert('Erro: ' + err.message);
    showState('setup');
  }
}

async function handleZipUpload(e) {
  const file = e.target.files[0];
  if (!file) return;

  if (!confirm(`Deseja importar o ZIP "${file.name}" diretamente para o banco?`)) return;

  showState('processing');
  updateProcessingStatus('Importando ZIP...', 50);

  const formData = new FormData();
  formData.append('zip_file', file);

  try {
    const response = await fetch('/parser/ingest-zip/', {
      method: 'POST',
      body: formData
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || 'Erro ao importar ZIP');
    }

    const result = await response.json();
    alert(`Sucesso! ${result.saved} questões importadas.`);
    location.reload();
  } catch (err) {
    alert('Erro: ' + err.message);
    showState('setup');
  }
}

async function saveToDatabase() {
  const btn = document.getElementById('btn-save-db');
  const originalText = btn.innerHTML;
  btn.disabled = true;
  btn.innerHTML = `<div class="loader"></div> SALVANDO...`;

  syncDataFromUI();

  try {
    const response = await fetch('/parser/save-to-db/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(currentExamData)
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || 'Erro ao salvar no banco');
    }

    const result = await response.json();
    alert(`Salvo com sucesso! ${result.saved} questões integradas ao banco.`);
  } catch (err) {
    alert('Erro ao salvar: ' + err.message);
  } finally {
    btn.disabled = false;
    btn.innerHTML = originalText;
  }
}

// --- EDITOR LOGIC ---
function loadEditor() {
  showState('editor');

  document.getElementById('meta-title').value = currentExamData.metadata.exam_title || '';
  document.getElementById('meta-year').value = currentExamData.metadata.year || '';
  document.getElementById('meta-type').value = (currentExamData.metadata.type || 'INTEGRADO').toUpperCase();

  renderAttachments();
  renderQuestions();
  updateStats();
  lucide.createIcons();
}

function renderAttachments() {
  const container = document.getElementById('attachments-container');
  if (!container) return;
  container.innerHTML = '';

  (currentExamData.global_attachments || []).forEach((att, idx) => {
    const card = document.createElement('div');
    card.className = 'card p-6 grid grid-cols-1 md:grid-cols-4 gap-6 relative group';
    card.innerHTML = `
      <div class="md:col-span-1 space-y-4">
        <div class="space-y-1">
          <label class="text-[10px] font-black text-slate-400 uppercase">ID</label>
          <input class="p-2" type="text" value="${att.id}" onchange="updateAttachmentField(${idx}, 'id', this.value)">
        </div>
        <div class="space-y-1">
          <label class="text-[10px] font-black text-slate-400 uppercase">Label</label>
          <input class="p-2" type="text" value="${att.label}" onchange="updateAttachmentField(${idx}, 'label', this.value)">
        </div>
        <div class="space-y-1">
          <label class="text-[10px] font-black text-slate-400 uppercase">Tipo</label>
          <select class="p-2" onchange="updateAttachmentField(${idx}, 'type', this.value)">
            <option value="text" ${att.type === 'text' ? 'selected' : ''}>Texto</option>
            <option value="image" ${att.type === 'image' ? 'selected' : ''}>Imagem</option>
          </select>
        </div>
      </div>
      <div class="md:col-span-3">
        ${att.type === 'text' ? `
          <div class="space-y-1 h-full">
            <label class="text-[10px] font-black text-slate-400 uppercase">Conteúdo</label>
            <textarea class="h-40 p-2" onchange="updateAttachmentField(${idx}, 'content', this.value)">${att.content || ''}</textarea>
          </div>
        ` : `
          <div class="space-y-2">
            <label class="text-[10px] font-black text-slate-400 uppercase">Visualização</label>
            <div class="relative rounded-xl overflow-hidden border border-slate-100 bg-slate-50 min-h-[200px] flex items-center justify-center p-4">
              ${att.image_data ? `
                <img src="${att.image_data}" class="max-w-full max-h-64 object-contain shadow-lg rounded-lg">
                <div class="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center gap-4">
                  <button onclick="openCropper('${att.id}')" class="flex flex-col items-center text-white hover:text-green-400">
                    <i data-lucide="crop" class="w-6 h-6"></i>
                    <span class="text-[10px] font-bold">AJUSTAR</span>
                  </button>
                  <label class="flex flex-col items-center text-white hover:text-green-400 cursor-pointer">
                    <i data-lucide="upload" class="w-6 h-6"></i>
                    <span class="text-[10px] font-bold">TROCAR</span>
                    <input type="file" class="hidden" accept="image/*" onchange="replaceImage(event, ${idx})">
                  </label>
                </div>
              ` : `
                <div class="text-center space-y-2">
                  <i data-lucide="image-plus" class="w-10 h-10 text-slate-300 mx-auto"></i>
                  <label class="cursor-pointer bg-green-700 text-white px-4 py-2 rounded-lg text-xs font-bold block">
                    CARREGAR IMAGEM
                    <input type="file" class="hidden" accept="image/*" onchange="replaceImage(event, ${idx})">
                  </label>
                </div>
              `}
            </div>
          </div>
        `}
      </div>
      <button onclick="removeAttachment(${idx})" class="absolute top-4 right-4 text-slate-300 hover:text-red-500 opacity-0 group-hover:opacity-100 transition-opacity">
        <i data-lucide="trash-2" class="w-5 h-5"></i>
      </button>
    `;
    container.appendChild(card);
  });
  lucide.createIcons();
}

function renderQuestions() {
  const container = document.getElementById('questions-container');
  if (!container) return;
  container.innerHTML = '';

  (currentExamData.questions || []).forEach((q, qIdx) => {
    const card = document.createElement('div');
    card.className = 'card overflow-hidden group';
    card.innerHTML = `
      <div class="bg-slate-50 px-6 py-4 border-b flex items-center justify-between">
        <div class="flex items-center gap-4">
          <div class="bg-slate-700 text-white w-10 h-10 rounded-full flex items-center justify-center font-black text-lg shadow-lg">${q.number}</div>
          <div class="space-y-1">
            <label class="text-[10px] font-black text-slate-400 uppercase tracking-widest leading-none">Matéria</label>
            <input type="text" value="${q.subject}" onchange="updateQuestionField(${qIdx}, 'subject', this.value)" class="bg-transparent border-none p-0 font-bold text-slate-700 focus:ring-0 w-32">
          </div>
        </div>
        <button onclick="removeQuestion(${qIdx})" class="text-slate-300 hover:text-red-500 transition-colors">
          <i data-lucide="trash-2" class="w-5 h-5"></i>
        </button>
      </div>
      <div class="p-8 space-y-6">
        <div class="space-y-1">
          <label class="text-[10px] font-black text-slate-400 uppercase tracking-widest">Enunciado</label>
          <textarea class="h-32 p-2" onchange="updateQuestionField(${qIdx}, 'text', this.value)">${q.text}</textarea>
        </div>
        
        <div class="space-y-2">
          <label class="text-[10px] font-black text-slate-400 uppercase tracking-widest">Anexos Vinculados</label>
          <div class="flex flex-wrap gap-2">
            ${(currentExamData.global_attachments || []).map(att => `
              <label class="flex items-center gap-2 px-3 py-1.5 rounded-lg border text-xs font-bold cursor-pointer transition-all ${q.local_attachments.includes(att.id) ? 'bg-green-600 border-green-600 text-white shadow-md' : 'bg-white text-slate-500 hover:border-green-300'}">
                <input type="checkbox" class="hidden" ${q.local_attachments.includes(att.id) ? 'checked' : ''} onchange="toggleQuestionAttachment(${qIdx}, '${att.id}')">
                ${att.label}
              </label>
            `).join('')}
          </div>
        </div>

        <div class="grid grid-cols-1 gap-3">
          <div class="flex items-center justify-between">
            <label class="text-[10px] font-black text-slate-400 uppercase tracking-widest">Alternativas</label>
        
          </div>
          ${q.alternatives.map((alt, aIdx) => `
            <div class="flex gap-3">
              <button onclick="setCorrectAnswer(${qIdx}, '${alt.letter}')" class="w-10 h-10 rounded-xl flex items-center justify-center font-black shrink-0 border-2 transition-all ${q.correct_answer === alt.letter ? 'bg-green-600 border-green-600 text-white shadow-lg' : 'bg-slate-50 border-slate-200 text-slate-400 hover:border-green-300'}">
                ${alt.letter}
              </button>
              <input type="text" value="${alt.text}" onchange="updateAlternative(${qIdx}, ${aIdx}, this.value)" class="bg-slate-50 px-2">
            </div>
          `).join('')}
        </div>
      </div>
    `;
    container.appendChild(card);
  });
  lucide.createIcons();
}

// --- CROPPER LOGIC ---
function openCropper(attId) {
  const att = currentExamData.global_attachments.find(a => a.id === attId);
  if (!att || !att.image_data) return;

  currentCroppingId = attId;
  const modal = document.getElementById('cropper-modal');
  const image = document.getElementById('cropper-image');

  image.src = att.image_data;
  modal.style.display = 'flex';

  if (cropper) cropper.destroy();

  cropper = new Cropper(image, {
    viewMode: 1,
    movable: true,
    zoomable: true,
    scalable: true,
    rotatable: true
  });
}

function closeCropper() {
  const modal = document.getElementById('cropper-modal');
  if (modal) modal.style.display = 'none';
  if (cropper) cropper.destroy();
  cropper = null;
}

function applyCrop() {
  const canvas = cropper.getCroppedCanvas({
    imageSmoothingQuality: 'high'
  });
  const base64 = canvas.toDataURL('image/jpeg', 0.9);

  const idx = currentExamData.global_attachments.findIndex(a => a.id === currentCroppingId);
  if (idx !== -1) {
    currentExamData.global_attachments[idx].image_data = base64;
    renderAttachments();
  }
  closeCropper();
}

function replaceImage(event, idx) {
  const file = event.target.files[0];
  if (!file) return;

  const reader = new FileReader();
  reader.onload = (e) => {
    currentExamData.global_attachments[idx].image_data = e.target.result;
    renderAttachments();
  };
  reader.readAsDataURL(file);
}

// --- ZIP EXPORT ---
async function exportZip() {
  syncDataFromUI();
  const zip = new JSZip();
  const imagesFolder = zip.folder("images");

  const exportData = JSON.parse(JSON.stringify(currentExamData));

  exportData.global_attachments.forEach(att => {
    if (att.type === 'image' && att.image_data) {
      const base64Data = att.image_data.split(',')[1];
      imagesFolder.file(`${att.id}.jpg`, base64Data, { base64: true });
      delete att.image_data;
      att.path = `images/${att.id}.jpg`;
    }
  });

  zip.file("prova.json", JSON.stringify(exportData, null, 2));
  const content = await zip.generateAsync({ type: "blob" });
  const url = URL.createObjectURL(content);
  const a = document.createElement('a');
  const filename = (exportData.metadata.year || '0000') + '-' + (exportData.metadata.type || 'prova').toLowerCase() + '.zip';
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

// --- UTILS & DATA SYNC ---
function switchTab(tabId) {
  syncDataFromUI();
  document.querySelectorAll('.tab-content').forEach(el => el.classList.add('hidden'));
  document.getElementById('tab-' + tabId).classList.remove('hidden');

  document.querySelectorAll('.sidebar-item').forEach(el => {
    el.classList.remove('active', 'bg-green-50', 'text-green-700');
    el.classList.add('text-slate-500');
  });

  const activeItem = document.querySelector(`[data-tab="${tabId}"]`);
  if (activeItem) {
    activeItem.classList.add('active', 'bg-green-50', 'text-green-700');
    activeItem.classList.remove('text-slate-500');
  }

  if (tabId === 'raw') {
    const previewData = JSON.parse(JSON.stringify(currentExamData));
    previewData.global_attachments.forEach(att => {
      if (att.type === 'image') {
        delete att.image_data;
        att.path = `images/${att.id}.jpg`;
      }
    });
    document.getElementById('raw-json-viewer').innerText = JSON.stringify(previewData, null, 2);
  }
}

function copyRawJson() {
  const text = JSON.stringify(currentExamData, null, 2);
  navigator.clipboard.writeText(text).then(() => {
    alert('JSON copiado para a área de transferência!');
  });
}

function syncDataFromUI() {
  if (!currentExamData) return;
  currentExamData.metadata.exam_title = document.getElementById('meta-title').value;
  currentExamData.metadata.year = parseInt(document.getElementById('meta-year').value);
  currentExamData.metadata.type = document.getElementById('meta-type').value;
}

function showState(state) {
  ['setup', 'processing', 'editor'].forEach(s => {
    const el = document.getElementById('state-' + s);
    if (el) el.classList.add('hidden');
  });
  const currentEl = document.getElementById('state-' + state);
  if (currentEl) currentEl.classList.remove('hidden');

  const footer = document.getElementById('editor-footer');
  if (footer) {
    if (state === 'editor') footer.classList.remove('hidden');
    else footer.classList.add('hidden');
  }
}

function updateProcessingStatus(text, progress) {
  const title = document.getElementById('processing-title');
  const bar = document.getElementById('progress-bar');
  if (title) title.innerText = text;
  if (bar) bar.style.width = progress + '%';
}

function updateStats() {
  const qCount = document.getElementById('stat-q-count');
  const aCount = document.getElementById('stat-a-count');
  if (qCount) qCount.innerText = currentExamData.questions.length;
  if (aCount) aCount.innerText = currentExamData.global_attachments.length;
}

function updateAttachmentField(idx, field, value) {
  const oldId = currentExamData.global_attachments[idx].id;
  currentExamData.global_attachments[idx][field] = value;
  
  // Se mudar o ID, atualiza as referências nas questões
  if (field === 'id' && oldId !== value) {
    currentExamData.questions.forEach(q => {
      const attIdx = q.local_attachments.indexOf(oldId);
      if (attIdx !== -1) q.local_attachments[attIdx] = value;
    });
  }

  if (field === 'type' || field === 'id' || field === 'label') {
    renderAttachments();
    renderQuestions();
  }
}

function removeAttachment(idx) {
  if (confirm('Remover este anexo?')) {
    currentExamData.global_attachments.splice(idx, 1);
    renderAttachments();
    renderQuestions();
    updateStats();
  }
}

function addAttachment() {
  currentExamData.global_attachments.push({
    id: 'Novo-Anexo-' + Date.now(),
    label: 'Novo Anexo',
    type: 'text',
    content: ''
  });
  renderAttachments();
  renderQuestions();
  updateStats();
}

function updateQuestionField(idx, field, value) {
  currentExamData.questions[idx][field] = value;
}

function updateAlternative(qIdx, aIdx, value) {
  currentExamData.questions[qIdx].alternatives[aIdx].text = value;
}

function setCorrectAnswer(qIdx, letter) {
  currentExamData.questions[qIdx].correct_answer = letter;
  renderQuestions();
}

function toggleQuestionAttachment(qIdx, attId) {
  const list = currentExamData.questions[qIdx].local_attachments;
  const index = list.indexOf(attId);
  if (index === -1) list.push(attId);
  else list.splice(index, 1);
  renderQuestions();
}

function addQuestion() {
  const nextNum = currentExamData.questions.length > 0 ?
    Math.max(...currentExamData.questions.map(q => q.number)) + 1 : 1;
  currentExamData.questions.push({
    number: nextNum,
    subject: 'portugues',
    text: '',
    local_attachments: [],
    alternatives: [
      { letter: 'A', text: '' },
      { letter: 'B', text: '' },
      { letter: 'C', text: '' },
      { letter: 'D', text: '' },
    ],
    correct_answer: 'A'
  });
  renderQuestions();
  updateStats();
}

function removeQuestion(idx) {
  if (confirm('Remover esta questão?')) {
    currentExamData.questions.splice(idx, 1);
    renderQuestions();
    updateStats();
  }
}

function resetApp() {
  if (confirm('Deseja descartar tudo e recomeçar?')) location.reload();
}
