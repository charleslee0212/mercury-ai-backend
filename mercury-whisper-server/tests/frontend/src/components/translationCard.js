import React, { useEffect, useRef } from 'react';
import { Box, Chip, Grid2 } from '@mui/material';
import { map } from '../options/languages';
import '../styles/translationCard.css';

const chipStyle = {
  height: 'auto',
  '& .MuiChip-label': {
    display: 'block',
    whiteSpace: 'normal',
    padding: '10px 12px 10px 12px',
  },
};

const TranslationCard = ({ language, partial, final }) => {
  const endOfCardRef = useRef();
  useEffect(() => {
    endOfCardRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [partial, final]);
  return (
    <>
      <div className="translation-card-label">{map[language]}</div>
      <Box className="translation-card">
        <Grid2
          container
          spacing={1}
          direction="column"
          sx={{
            alignItems: 'flex-end',
          }}
        >
          {final.map((transcript, index) => (
            <Chip
              color="secondary"
              sx={chipStyle}
              className="final"
              label={transcript}
              key={`final-chip-${index}`}
            />
          ))}
          {partial ? (
            <Chip
              color="secondary"
              sx={chipStyle}
              className="partial"
              label={partial}
            />
          ) : (
            <></>
          )}
        </Grid2>
        <div className="end-of-card" ref={endOfCardRef}></div>
      </Box>
    </>
  );
};

export default TranslationCard;
