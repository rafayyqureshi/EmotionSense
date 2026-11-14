(function (root) {
    'use strict';
    function escapeHtml(value) {
        const entities = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' };
        return String(value).replace(/[&<>"']/g, character => entities[character]);
    }
    const api = { escapeHtml };
    if (typeof module === 'object' && module.exports) {
        module.exports = api;
    } else {
        root.EmotionText = api;
    }
}(typeof window === 'undefined' ? {} : window));
