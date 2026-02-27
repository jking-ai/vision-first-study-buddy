import React from "react";
import {
  Box,
  Typography,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Paper,
  Divider,
  Chip,
  Stack,
} from "@mui/material";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";

function StudyGuideView({ studyGuide }) {
  if (!studyGuide) return null;

  const { title, summary, sections, source_materials, generated_at } = studyGuide;

  return (
    <Paper sx={{ p: 3 }} className="study-guide-print">
      {/* Title & summary */}
      <Typography variant="h1" gutterBottom>
        {title}
      </Typography>
      <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
        {summary}
      </Typography>

      <Divider sx={{ mb: 2 }} />

      {/* Sections */}
      {sections?.map((section, i) => (
        <Accordion key={i} defaultExpanded>
          <AccordionSummary expandIcon={<ExpandMoreIcon />}>
            <Typography variant="h6">{section.heading}</Typography>
          </AccordionSummary>
          <AccordionDetails>
            <Typography variant="body1" sx={{ whiteSpace: "pre-line", mb: 2 }}>
              {section.content}
            </Typography>

            {/* Key terms */}
            {section.key_terms?.length > 0 && (
              <Box sx={{ mt: 1 }}>
                <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                  Key Terms
                </Typography>
                <Stack spacing={1}>
                  {section.key_terms.map((kt, j) => (
                    <Box key={j}>
                      <Typography variant="body2">
                        <strong>{kt.term}</strong> — {kt.definition}
                      </Typography>
                    </Box>
                  ))}
                </Stack>
              </Box>
            )}
          </AccordionDetails>
        </Accordion>
      ))}

      {/* Footer */}
      <Divider sx={{ mt: 3, mb: 2 }} />
      <Stack direction="row" spacing={2} alignItems="center" flexWrap="wrap">
        <Chip
          label={`${source_materials?.length || 0} source material${source_materials?.length !== 1 ? "s" : ""}`}
          size="small"
          variant="outlined"
        />
        {generated_at && (
          <Typography variant="caption" color="text.secondary">
            Generated {new Date(generated_at).toLocaleString()}
          </Typography>
        )}
      </Stack>
    </Paper>
  );
}

export default StudyGuideView;
