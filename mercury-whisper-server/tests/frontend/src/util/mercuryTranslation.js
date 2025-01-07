export default async (body) => {
  const url = 'https://api.mercury-ai.io/translation';
  try {
    const resp = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
    });
    if (!resp.ok) {
      throw new Error(`HTTP error! status: ${resp.status}`);
    }
    return await resp.json();
  } catch (e) {
    console.log(e);
    return false;
  }
};
