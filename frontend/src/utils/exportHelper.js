import * as XLSX from 'xlsx';

export const exportToExcel = (data, filename = 'SYConv_Extracted_Words.xlsx') => {
    if (!data || data.length === 0) {
        alert("No data to export!");
        return;
    }

    // Clean data for the user
    const cleanData = data.map(({ word, pos, meaning, is_idiom }) => ({
        'Word / Phrase': word,
        'Part of Speech': pos,
        'Meaning': meaning,
        'Is Idiom': is_idiom ? 'Yes' : 'No'
    }));

    const worksheet = XLSX.utils.json_to_sheet(cleanData);
    const workbook = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(workbook, worksheet, "Vocabulary");

    XLSX.writeFile(workbook, filename);
};
