import React, { useEffect, useState } from 'react';
import { Grid2 } from '@mui/material';
import TranslationCard from './translationCard';
import mercuryTranslation from '../util/mercuryTranslation';

const getTranslations = async ({ model, text, languages }) => {
  const x = await mercuryTranslation({
    model: model,
    transcription: text,
    languages: languages,
  });
  console.log(x);
  const completion = x.completion;
  const { translations } = JSON.parse(completion);
  return translations;
};

const Translation = ({ model, languages, data }) => {
  const [partialTranslation, setPartialTranslation] = useState({});
  const [finalTranslation, setFinalTranslation] = useState([]);

  useEffect(() => {
    console.log(data);
    if (Object.keys(data).length) {
      (async () => {
        const type = data.type;
        switch (type) {
          case 'partial':
            const partial_translations = await getTranslations({
              model: model,
              text: data.text,
              languages: languages,
            });
            setPartialTranslation(partial_translations);
            break;
          case 'final':
            const final_translations = await getTranslations({
              model: model,
              text: data.text,
              languages: languages,
            });
            setPartialTranslation({});
            setFinalTranslation((prev) => {
              const arr = [...prev];
              arr.push(final_translations);
              return arr;
            });
            break;
          default:
            console.log('Unspecified Type!');
        }
      })();
    }
  }, [data]);

  return (
    <Grid2
      container
      className="mercury-translation"
      direction="row"
      spacing={2}
      height="100%"
      size={{ xs: 12, md: 6 }}
    >
      {languages.map((language, index) => (
        <Grid2
          container
          direction="column"
          key={index}
          size={{ xs: 12, md: 6 }}
          position="relative"
          height="100%"
        >
          <TranslationCard
            language={language}
            partial={partialTranslation[language]}
            final={finalTranslation.map((translation) => translation[language])}
          />
        </Grid2>
      ))}
    </Grid2>
  );
};

export default Translation;
