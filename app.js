const $ = (id) => document.getElementById(id);

function status(message, good = false) {
  const element = $('status');
  element.textContent = message;
  element.style.color = good ? '#8cff00' : '#8b9aaa';
}

$('loadProfiles').addEventListener('click', async () => {
  const apiKey = $('api_key').value.trim();
  if (!apiKey) return status('HÃY NHẬP API KEY TRƯỚC.');
  const button = $('loadProfiles');
  button.disabled = true;
  button.textContent = 'ĐANG TẢI...';
  status('ĐANG KẾT NỐI NEXTDNS...');
  try {
    const response = await fetch('/api/profiles', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({api_key: apiKey})
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'KHÔNG TẢI ĐƯỢC PROFILE.');
    const select = $('profile_id');
    select.innerHTML = data.profiles.map(p => `<option value="${p.id}">${p.name} — ${p.id}</option>`).join('');
    select.disabled = false;
    status(`ĐÃ TẢI ${data.profiles.length} PROFILE.`, true);
  } catch (error) {
    status(error.message);
  } finally {
    button.disabled = false;
    button.textContent = 'TẢI PROFILE';
  }
});

$('builder').addEventListener('submit', async (event) => {
  event.preventDefault();
  if ($('profile_id').disabled) return status('HÃY TẢI VÀ CHỌN PROFILE TRƯỚC.');
  const button = $('submitBtn');
  button.disabled = true;
  button.textContent = 'ĐANG XỬ LÝ...';
  status('ĐANG CẬP NHẬT DANH SÁCH VÀ TẠO FILE...');
  try {
    const response = await fetch('/api/update', { method: 'POST', body: new FormData(event.target) });
    if (!response.ok) {
      const data = await response.json();
      throw new Error(data.error || 'CÓ LỖI KHI XỬ LÝ.');
    }
    const blob = await response.blob();
    const disposition = response.headers.get('Content-Disposition') || '';
    const match = disposition.match(/filename="?([^";]+)"?/i);
    const filename = match ? match[1] : 'nextdns-config.mobileconfig';
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    link.click();
    URL.revokeObjectURL(url);
    const rawResult = response.headers.get('X-NextDNS-Result');
    let message = 'ĐÃ HOÀN TẤT — FILE ĐÃ ĐƯỢC TẢI XUỐNG.';
    if (rawResult) {
      const result = JSON.parse(rawResult);
      const added = result.denylist.added.length + result.allowlist.added.length;
      message += ` THÊM MỚI ${added} MIỀN.`;
    }
    status(message, true);
  } catch (error) {
    status(error.message);
  } finally {
    button.disabled = false;
    button.textContent = 'CẬP NHẬT & TẢI FILE';
  }
});
