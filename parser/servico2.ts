import { GoogleGenAI } from "@google/genai";
import { PageData } from "@/src/lib/pdfWorker";

const ai = new GoogleGenAI({ apiKey: process.env.GEMINI_API_KEY! });

export interface ExamJson {
  metadata: {
    exam_title: string;
    year: number;
    type: string;
  };
  global_attachments: Array<{
    id: string;
    label: string;
    type: "text" | "image";
    content?: string;
    image_reference?: {
      page: number;
      bbox: [number, number, number, number];
    };
    image_data?: string;
  }>;
  questions: Array<{
    number: number;
    subject: string;
    text: string;
    local_attachments: string[];
    alternatives: Array<{
      letter: string;
      text: string;
    }>;
    correct_answer: string;
  }>;
}

export async function transformExamToJson(pages: PageData[], answerKeyText?: string): Promise<string> {
  const fullText = pages.map((p, i) => `--- PÁGINA ${i + 1} ---\n${p.text}`).join("\n\n");
  
  const imageParts = pages.map(p => ({
    inlineData: {
      data: p.image.split(',')[1],
      mimeType: "image/jpeg"
    }
  }));

  const prompt = `
Contexto: Você é um Especialista em Extração de Dados de Documentos Técnicos. Sua missão é converter uma prova do IFMA em um JSON estruturado para ingestão em banco de dados.

${answerKeyText ? `GABARITO DETECTADO: Use estas informações para identificar a alternativa correta:\n${answerKeyText}\n` : ''}

REGRAS CRÍTICAS DE EXTRAÇÃO:
1. METADADOS: O campo 'exam_title' DEVE seguir o formato: "SELETIVO TÉCNICO – [TIPO] [ANO]" (ex: SELETIVO TÉCNICO – SUBSEQUENTE 2024).
2. ANEXOS GLOBAIS (ZONA DE ALERTA):
   - Capture TODOS os textos de apoio, figuras, tabelas, quadros, gráficos, diagramas E TRECHOS DE CONTEXTO.
   - TRECHOS: Mesmo que um texto seja curto (ex: "Considere o trecho..."), se ele serve de base para responder questões, você DEVE extraí-lo como um anexo global.
   - LABEL: O campo 'label' deve ser idêntico ao que aparece na prova (ex: "Texto 1", "Figura 2", "Quadro 01", "Trecho para questões 03 a 05"). 
   - REGRAS DE LABEL: 
     - NÃO adicione descrições após o nome (ex: use "Texto 2", NÃO USE "Texto 2: Estatísticas...").
     - Se o texto indicar que é para questões específicas, inclua no label (ex: "Trecho para Questões 05 a 09").
   - SE FOR TEXTO PURO: Copie o conteúdo INTEGRAL. Não resuma.
   - SE FOR QUALQUER ELEMENTO VISUAL OU ESTRUTURADO (Tabelas, Quadros, Gráficos, Mapas, Figuras de Matemática, Diagramas): 
     - É EXPRESSAMENTE PROIBIDO converter tabelas ou quadros para texto ou markdown.
     - Você DEVE capturar o bbox [ymin, xmin, ymax, xmax] (coordenadas 0-1000) e definir o type como 'image'.
     - Se houver um Quadro ou Tabela, não extraia os dados em texto; capture a área visual como imagem.
   - ATENÇÃO: Se uma questão tiver imagens essenciais para sua resolução, capture-as como anexo e vincule o ID na questão. NÃO IGNORE elementos visuais.
3. QUESTÕES:
   - Extraia número, matéria (subject: portugues, matematica, etc).
   - 'text': O enunciado deve ser fiel e completo.
   - 'local_attachments': Liste os IDs (ex: "Figura-1", "Texto-2") que a questão utiliza ou faz referência.
   - 'alternatives': Extraia todas as opções fielmente.
   - 'correct_answer': A letra correta (A, B, C, D ou E).

ESQUEMA JSON:
{
  "metadata": { "exam_title": "string", "year": number, "type": "string" },
  "global_attachments": [
    { "id": "Texto-1", "label": "Texto 1", "type": "text", "content": "..." },
    { "id": "Figura-1", "label": "Figura 1", "type": "image", "image_reference": { "page": 1, "bbox": [ymin, xmin, ymax, xmax] } }
  ],
  "questions": [
    {
      "number": 1,
      "subject": "string",
      "text": "string",
      "local_attachments": ["ID"],
      "alternatives": [ { "letter": "A", "text": "..." } ],
      "correct_answer": "A"
    }
  ]
}

REQUISITO DE ARQUIVOS:
- O JSON gerado por você conterá 'image_reference'. 
- No processamento final (pelo sistema), o campo 'image_reference' será substituído por um campo 'path' apontando para 'images/ID.jpg'.
- Portanto, garanta que cada imagem essencial tenha um ID único e descritivo.

Retorne APENAS o JSON.
Conteúdo da Prova:
${fullText}
`;

  const response = await ai.models.generateContent({
    model: "gemini-3-flash-preview",
    contents: {
      parts: [
        { text: prompt },
        ...imageParts
      ]
    },
    config: {
      responseMimeType: "application/json"
    }
  });

  return response.text || "";
}
