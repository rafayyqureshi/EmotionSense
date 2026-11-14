const test = require('node:test');
const assert = require('node:assert/strict');
const { escapeHtml } = require('../static/js/text-utils.js');

test('untrusted comment markup becomes text', () => {
    const attack = '<img src=x onerror="alert(1)">';
    assert.equal(escapeHtml(attack), '&lt;img src=x onerror=&quot;alert(1)&quot;&gt;');
});
test('quotes and ampersands are encoded', () => {
    assert.equal(escapeHtml("Tom's <tag> & \"text\""), 'Tom&#39;s &lt;tag&gt; &amp; &quot;text&quot;');
});
test('ordinary Unicode text remains readable', () => {
    assert.equal(escapeHtml('Rafay — خوش آمدید'), 'Rafay — خوش آمدید');
});
