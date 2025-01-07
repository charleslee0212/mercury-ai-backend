import React, { useEffect, useState } from 'react';
import { Grid2 } from '@mui/material';
import TranslationCard from './translationCard';
import mercuryTranslation from '../util/mercuryTranslation';

const Translation = ({ model, languages, partial, final }) => {
  const [partialTranslation, setPartialTranslation] = useState({});
  const [finalTranslation, setFinalTranslation] = useState([]);

  useEffect(() => {
    (async () => {
      if (partial) {
        const { completion } = await mercuryTranslation({
          model: model,
          transcription: partial,
          languages: languages,
        });
        const { translations } = JSON.parse(completion);
        setPartialTranslation(translations);
      }
    })();
  }, [partial]);

  useEffect(() => {
    (async () => {
      if (final.length) {
        const { completion } = await mercuryTranslation({
          model: model,
          transcription: final[final.length - 1],
          languages: languages,
        });
        const { translations } = JSON.parse(completion);
        setPartialTranslation({});
        setFinalTranslation((prev) => {
          const arr = [...prev];
          arr.push(translations);
          return arr;
        });
      }
    })();
  }, [final]);

  return (
    <Grid2 container direction="row" spacing={2} className="translation">
      {languages.map((language, index) => (
        <Grid2 key={index} size={6}>
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
