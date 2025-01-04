import {
  SecretsManagerClient,
  GetSecretValueCommand,
} from '@aws-sdk/client-secrets-manager';
import OpenAI from 'openai/index.mjs';

export const handler = async (event) => {
  const {
    body: { model, transcription, languages },
  } = event;

  const secret_name = 'openai_api_token';

  const aws_client = new SecretsManagerClient({
    region: 'us-west-1',
  });

  let secretResp;

  try {
    secretResp = await aws_client.send(
      new GetSecretValueCommand({
        SecretId: secret_name,
        VersionStage: 'AWSCURRENT',
      })
    );
  } catch (error) {
    console.log({ type: 'aws-secrets', message: error });
    throw error;
  }

  const secret = secretResp.SecretString;

  console.log(secret);

  const openai_client = new OpenAI({
    apiKey: secret,
  });

  const completion = await openai_client.chat.completions.create({
    model: model,
    messages: [
      {
        role: 'developer',
        content: `You are a translator that will translate incomming transcriptions to the requested languages.
          You will ONLY respond with JSON.
          Make any corrections necessary to improve the translation.
          JSON format: {"translations":[{"language":"en","translation":"Hello world!"},{"language":"ko","translation":"안녕 세상!"}]}`,
      },
      {
        role: 'user',
        content: '{"transcription":"Hello World!","languages":["ko","es"]}',
      },
      {
        role: 'assistant',
        content:
          '{"translations":[{"language":"ko","translation":"안녕 세상!"},{"language":"es","translation":"¡Hola Mundo!"}]}',
      },
      {
        role: 'user',
        content: JSON.stringify({
          transcription: transcription,
          languages: languages,
        }),
      },
    ],
  });

  return {
    statusCode: 200,
    body: completion,
  };
};
