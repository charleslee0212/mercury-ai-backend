import React, { useEffect, useRef } from 'react';
import { Box, Chip, Grid2 } from '@mui/material';
import '../styles/transcription.css';

const chipStyle = {
  height: 'auto',
  '& .MuiChip-label': {
    display: 'block',
    whiteSpace: 'normal',
    padding: '10px 12px 10px 12px',
  },
};

const Transcription = ({ partial, final }) => {
  const endOfCardRef = useRef();
  useEffect(() => {
    endOfCardRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [partial, final]);
  return (
    <Box className="transcription">
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
            color="primary"
            sx={chipStyle}
            className="final"
            label={transcript}
            key={`final-chip-${index}`}
          />
        ))}
        {partial ? (
          <Chip
            color="primary"
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
  );
};

export default Transcription;
